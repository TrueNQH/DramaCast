"""End-to-end job: crawl -> script -> TTS (+ B-roll) -> inputProps.json -> Remotion render.

CLI: python -m app.pipeline --topic "nuôi gạch rêu" --template news --mock   (omit --template for a menu)
Resume with the same script: python -m app.pipeline --script ../outputs/<jobId>_script.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import sys
import uuid
from pathlib import Path
from typing import Callable, NamedTuple

from app.config import BGM_DIR, BGM_VOLUME, OUTPUTS_DIR, PUBLIC_DIR
from app.schemas import Card, Segment, Template, VideoProps, frames_for
from app.services import remotion_bridge, scriptwriter, tts_engine
from app.services.crawler import fetch_posts
from app.services.media_fetcher import Media, MediaFetcher

log = logging.getLogger(__name__)

# Shown in the start-up menu and by GET /templates.
TEMPLATES: dict[str, str] = {
    "news": "Tin tức giải thích: B-roll phía trên, khung màu thương hiệu + phụ đề phía dưới, thẻ tiêu đề mở đầu",
    "story": "Đọc truyện Threads: nền gameplay, thẻ bài đăng mở đầu, các đoạn truyện hiện dần theo lời đọc",
    "techcards": "Bản tin motion graphics: nền pastel, mỗi cảnh một tấm thẻ (chữ lớn, ảnh, gạch đầu dòng, VS, follow)",
    "social": "Radio Lofi: thẻ bài đăng kính mờ trên nền video lặp, phụ đề karaoke",
}
DEFAULT_BG_VIDEO = "assets/bg_rain_cafe.mp4"
FPS = 30
AUDIO_EXTS = {".mp3", ".m4a", ".wav", ".ogg"}


class Bgm(NamedTuple):
    file: str  # relative to public/
    credit: str


def _asset_or_empty(relative: str) -> str:
    return relative if (PUBLIC_DIR / relative).exists() else ""


def _pick_bgm() -> Bgm | None:
    """Random track from public/assets/bgm/; credits come from an optional credits.json {file: credit}."""
    tracks = [f for f in BGM_DIR.glob("*") if f.suffix.lower() in AUDIO_EXTS] if BGM_DIR.exists() else []
    if not tracks:
        return None
    track = random.choice(tracks)
    credits_file = BGM_DIR / "credits.json"
    credits = json.loads(credits_file.read_text(encoding="utf-8")) if credits_file.exists() else {}
    return Bgm(remotion_bridge.public_path(track), credits.get(track.name, track.name))


async def run_job(
    topic: str,
    template: Template = "news",
    *,
    job_id: str | None = None,
    use_mock: bool = False,
    brand_name: str = "DRAMACAST",
    brand_color: str = "#8F1210",
    on_progress: Callable[[str], None] = lambda _: None,
    script_file: Path | None = None,
    mock_file: Path | None = None,
) -> Path:
    job_id = job_id or uuid.uuid4().hex[:10]

    if script_file:
        script = scriptwriter.Script.model_validate_json(script_file.read_text(encoding="utf-8"))
    else:
        on_progress("crawling")
        posts = await asyncio.to_thread(fetch_posts, topic, use_mock, mock_file)
        on_progress("writing_script")
        script = await asyncio.to_thread(scriptwriter.write_script, posts, template, topic)
    # Kept so a failed run can be resumed with --script without another LLM call.
    OUTPUTS_DIR.mkdir(exist_ok=True)
    (OUTPUTS_DIR / f"{job_id}_script.json").write_text(script.model_dump_json(indent=2), encoding="utf-8")

    on_progress("synthesizing")
    job_dir = remotion_bridge.reset_job_dir()
    subtitle_mode = "word" if template == "social" else "phrase"
    segments: list[Segment] = []
    credits: list[str] = []
    background: Media | None = None
    narrations = [part.narration for part in script.segments]
    tts_results = await tts_engine.synthesize_all(narrations, job_dir, subtitle_mode)
    fetcher = MediaFetcher() if template in ("news", "story", "techcards") else None
    try:
        if template == "story":
            total = sum(t.duration_in_seconds for t in tts_results if t)
            background = await fetcher.fetch_background(job_dir / "gameplay", total)
            if background:
                credits.append(f"background: {background.credit}")
        i = 0
        for n, (part, tts) in enumerate(zip(script.segments, tts_results), start=1):
            if tts is None:
                continue
            i += 1
            media = None
            wants_media = template == "news" or (template == "techcards" and part.card and part.card.type == "media")
            if fetcher and wants_media and part.media_query:
                media = await fetcher.fetch(part.media_query, job_dir / f"media_{i}", tts.duration_in_seconds)
                if media:
                    credits.append(f"segment {i}: {media.credit}")
            segments.append(
                Segment(
                    id=i,
                    platform=part.platform,
                    authorName=part.author_name,
                    authorHandle=part.author_handle,
                    cardContent=part.card_content[:220],
                    likesCount=part.likes_count,
                    sentiment=part.sentiment,
                    audioFile=remotion_bridge.public_path(tts.audio_path),
                    durationInSeconds=tts.duration_in_seconds,
                    durationInFrames=frames_for(tts.duration_in_seconds, FPS),
                    subtitles=tts.subtitles,
                    mediaFile=remotion_bridge.public_path(media.path) if media else None,
                    mediaType=media.media_type if media else None,
                    mediaDurationInSeconds=media.duration_in_seconds if media else None,
                    card=Card.model_validate(part.card.model_dump()) if part.card else None,
                )
            )
            log.info("segment %d/%d ready", n, len(script.segments))
    finally:
        if fetcher:
            await fetcher.aclose()

    bgm = _pick_bgm()
    if bgm:
        credits.append(f"music: {bgm.credit}")

    props = VideoProps(
        jobId=job_id,
        template=template,
        topicTitle=script.topic_title,
        topicHighlight=script.topic_highlight,
        brandName=brand_name,
        brandColor=brand_color,
        fps=FPS,
        bgVideoFile=remotion_bridge.public_path(background.path) if background else _asset_or_empty(DEFAULT_BG_VIDEO),
        bgVideoDurationInSeconds=background.duration_in_seconds if background else None,
        sourceLabel=script.source_label,
        bgmAudioFile=bgm.file if bgm else "",
        bgmVolume=BGM_VOLUME,
        segments=segments,
    )

    on_progress("rendering")
    out_file = await remotion_bridge.render(props)
    if credits:
        # Pixabay asks API users to credit sources; paste this into the video description.
        out_file.with_name(f"{job_id}_credits.txt").write_text("\n".join(credits), encoding="utf-8")
    return out_file


def _choose_template() -> str:
    names = list(TEMPLATES)
    if not sys.stdin.isatty():
        return names[0]
    print("Chọn template video:")
    for k, name in enumerate(names, start=1):
        print(f"  {k}. {name:<10} {TEMPLATES[name]}")
    while True:
        answer = input(f"Nhập số 1-{len(names)} [1]: ").strip() or "1"
        if answer.isdigit() and 1 <= int(answer) <= len(names):
            return names[int(answer) - 1]
        if answer in TEMPLATES:
            return answer


def main() -> None:
    parser = argparse.ArgumentParser(description="Render one DramaCast video")
    parser.add_argument("--topic", default="")
    parser.add_argument("--template", choices=list(TEMPLATES), help="omit to choose from a menu")
    parser.add_argument("--mock", action="store_true", help="use backend/app/data/mock_posts.json instead of Agent-Reach")
    parser.add_argument("--mock-file", type=Path, help="use this posts JSON (same shape as mock_posts.json) instead of crawling")
    parser.add_argument("--script", type=Path, help="reuse a saved *_script.json instead of crawling + LLM")
    args = parser.parse_args()
    template = args.template or _choose_template()
    logging.basicConfig(level=logging.INFO)
    # httpx logs full request URLs at INFO, which include the Pixabay key as a query parameter.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    out = asyncio.run(
        run_job(
            args.topic,
            template,
            use_mock=args.mock,
            script_file=args.script,
            mock_file=args.mock_file,
            on_progress=lambda s: log.info("stage: %s", s),
        )
    )
    print(out)


if __name__ == "__main__":
    main()
