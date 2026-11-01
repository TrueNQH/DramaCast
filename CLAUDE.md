# Project: DramaCast Studio MVP (FastAPI + Edge-TTS + Remotion Video Engine)

## 1. Overview
An automated 9:16 vertical video generation pipeline that:
1. Crawls trending social posts & top comments (X/Twitter, Reddit, XiaoHongShu, YouTube) via `Agent-Reach`.
2. Rewrites raw data into a humorous, teasing, drama-commentary script that baits viewer comments, using an OpenAI-compatible LLM endpoint (code default Groq `openai/gpt-oss-120b`; the local setup uses Gemini 3.1 Pro through a `gemini-web2api` proxy at `127.0.0.1:8081` with the user's cookie, prepared by `backend/scripts/prepare_gemini_auth.py`).
3. Synthesizes natural Vietnamese speech (`edge-tts`) and extracts exact word/sentence-level timestamps.
4. Passes structured JSON props (`inputProps.json`) into a **Remotion (React + TypeScript + Tailwind CSS)** engine to programmatically render a polished 1080x1920 MP4 video with glassmorphism social cards, animated subtitles, audio waveform, and Lofi background music.

## 2. Tech Stack & Monorepo Architecture
- **Backend (`/backend` - Python 3.11+):**
  - `FastAPI` + `Pydantic v2`: API server, job orchestration, and strict JSON schema validation.
  - `Agent-Reach` CLI wrapper (`subprocess`): Zero-fee social media scraping.
  - `edge-tts`: Free Microsoft Neural Vietnamese TTS (`vi-VN-HoaiMyNeural` & `vi-VN-NamMinhNeural`) with `SubMaker` for word/sentence boundary timestamps.
  - `mutagen` or `ffprobe`: Accurate audio duration inspection.
- **Video Engine (`/remotion-video` - Node.js 20+ / TypeScript):**
  - `Remotion` (`@remotion/cli`, `@remotion/renderer`, `@remotion/media-utils`).
  - `React 18` + `TypeScript` + `Tailwind CSS`: Component-based 9:16 video templates.
  - `lucide-react`: Platform icons (X, Reddit, Quotes, Verified badges, Heart/Reply counters).

## 3. Directory Structure
- `backend/app/main.py` : FastAPI entry point & pipeline endpoints
- `backend/app/schemas.py` : Shared Pydantic models (matches Remotion TypeScript `VideoProps` schema)
- `backend/app/services/crawler.py` : Agent-Reach CLI wrapper + fallback mock data loader
- `backend/app/services/scriptwriter.py` : LLM prompt & script generator (OpenAI-compatible `/chat/completions` at `LLM_BASE_URL`; `response_format: json_object` when `LLM_JSON_MODE=true`; reply JSON is Pydantic-validated with retry)
- `backend/app/services/tts_engine.py` : Narration audio + subtitles; `synthesize_all` dispatches on `TTS_ENGINE` (`gemini` default, falls back to per-segment edge-tts)
- `backend/app/services/gemini_tts.py` : Whole-script Gemini TTS (`gemini-3.8-flash-tts`, one Interactions API call per video, cached) + Groq Whisper word timestamps aligned back to the script; audio cut into `seg_{n}.wav` mid-pause
- `backend/app/services/remotion_bridge.py` : Copies assets to Remotion `public/current_job/` and runs `npx remotion render`
- `backend/app/services/media_fetcher.py` : B-roll for the `news` template: Pixabay videos/photos -> Openverse CC0 photos (opt-in, `OPENVERSE_FALLBACK`) -> local `public/assets/broll/` (Pexels no longer issues API keys)
- `backend/app/pipeline.py` : End-to-end job runner (also a CLI: `python -m app.pipeline --template news --mock`)
- `backend/requirements.txt` : Python dependencies
- `remotion-video/package.json` : Node dependencies & Remotion scripts
- `remotion-video/remotion.config.ts` : Remotion configuration (Tailwind webpack override)
- `remotion-video/src/index.ts` : Remotion registerRoot entry
- `remotion-video/src/Root.tsx` : `<Composition>` definition with `calculateMetadata` for dynamic duration
- `remotion-video/src/types/schema.ts` : Zod / TypeScript interfaces matching backend `inputProps.json`
- `remotion-video/src/Composition.tsx` : Master 9:16 timeline (`<Series>` sequencing segments + global BGM + Lofi background)
- `remotion-video/src/components/SocialCard.tsx` : Glassmorphism post/comment card with `spring()` entrance animation
- `remotion-video/src/components/SubtitleTrack.tsx` : Synchronized word/phrase karaoke subtitle display
- `remotion-video/src/components/LofiBackground.tsx` : Loopable background video/image with dark vignette & blur overlay
- `remotion-video/src/NewsComposition.tsx` : `news` template timeline (B-roll top, brand-colored caption panel bottom)
- `remotion-video/src/components/news/` : `BrollMedia` (Ken Burns image/clip), `TitleCard` (opening hook card), `NewsSubtitle` (phrase captions)
- `remotion-video/src/StoryComposition.tsx` + `components/story/` : `story` template (gameplay background, `ThreadsPostCard` hook, `StoryTextBox` paragraphs revealed phrase by phrase, paged at ~380 chars)
- `remotion-video/src/TechCardsComposition.tsx` + `components/techcards/` : `techcards` template (`Chrome`: pastel background, brand header, source pill; `Cards`: hero / media / bullets / versus / quote / cta; `motion.ts`: blur-in / pop helpers)
- `remotion-video/public/assets/gameplay/` : optional local background clips for `story` (else a Pixabay satisfying/parkour clip)
- `remotion-video/public/assets/bgm/` : Lofi BGM tracks (Pixabay Music) + `credits.json`; one is picked at random per job, played by `components/BackgroundMusic.tsx` (loop, 1s fade-in, 1.5s fade-out)
- `remotion-video/public/assets/` : Static Lofi `.mp4` loops, `.mp3` BGM tracks, and custom fonts (`Be Vietnam Pro`)
- `remotion-video/public/current_job/` : Dynamically generated segment `.mp3` files and `inputProps.json`
- `outputs/` : Final rendered `.mp4` videos

## 4. Shared Data Contract (`inputProps.json` Schema)
Both Python (`schemas.py`) and TypeScript (`src/types/schema.ts`) MUST strictly adhere to this JSON contract:
- `jobId`: string
- `template`: `"social"` | `"news"` | `"story"` | `"techcards"` (Default: `"social"`; `Composition.tsx` dispatches on it)
- `topicTitle`: string (Main hook header shown at top badge / news title card)
- `topicHighlight`: string (Exact substring of `topicTitle` drawn in `brandColor` on the news title card; may be `""`)
- `brandName`: string (Default: `"DRAMACAST"`; news title card + watermark)
- `brandColor`: string (Default: `"#8F1210"`; news caption panel)
- `fps`: number (Default: `30`)
- `width`: number (Default: `1080`)
- `height`: number (Default: `1920`)
- `bgVideoFile`: string (e.g., `"assets/bg_rain_cafe.mp4"`; `story`: the gameplay clip)
- `bgVideoDurationInSeconds`: number | null (`story` gameplay length, used to `<Loop>` it)
- `sourceLabel`: string (`techcards` bottom pill, e.g. `"threads.net"`; from the script's `source_label`)
- `bgmAudioFile`: string (e.g., `"assets/bgm_lofi_chill.mp3"`)
- `bgmVolume`: number (Default: `0.12`)
- `segments`: Array of Segment objects:
  - `id`: number
  - `platform`: `"twitter"` | `"reddit"` | `"xiaohongshu"` | `"youtube"` | `"narrator"`
  - `authorName`: string (e.g., `"@elonmusk"`, `"u/tech_insider"`)
  - `authorHandle`: string
  - `cardContent`: string (Translated concise quote/post displayed inside the UI card, max 220 chars)
  - `likesCount`: string (e.g., `"14.2K"`)
  - `sentiment`: `"neutral"` | `"drama"` | `"healing"`
  - `audioFile`: string (Relative to `public/`, e.g., `"current_job/seg_1.mp3"`)
  - `durationInSeconds`: number (Exact audio length + `0.25s` breathing pause)
  - `durationInFrames`: number (`Math.ceil(durationInSeconds * fps)`)
  - `subtitles`: Array of `{ text: string, startMs: number, endMs: number }` (word-level for `social`, phrase-level for `news`)
  - `mediaFile`: string | null (`news` only: B-roll relative to `public/`, e.g. `"current_job/media_3.mp4"`)
  - `mediaType`: `"image"` | `"video"` | null
  - `mediaDurationInSeconds`: number | null (clip length, used to `<Loop>` short clips)
  - `card`: object | null (`techcards` only): `{ type: "hero"|"media"|"bullets"|"versus"|"quote"|"cta", kicker, headline, subline, items: string[], versus: { leftLabel, leftText, rightLabel, rightText, winner: "left"|"right"|"" } | null }`

## 5. Key Implementation Rules for Claude Code
1. **Per-Segment Audio & Sync (`tts_engine.py`):**
   - Synthesize each segment independently using `edge_tts.Communicate(text, voice="vi-VN-HoaiMyNeural", rate="+12%", pitch="+2Hz")` (upbeat pacing for the humorous drama tone; overridable via `TTS_RATE` / `TTS_PITCH` in `backend/.env`).
   - Stream events from `communicate.stream()`: capture `audio` chunks to write `seg_{id}.mp3` into `remotion-video/public/current_job/`, and capture `WordBoundary` / `SentenceBoundary` events to build the `subtitles` array (`startMs`, `endMs`, `text`).
   - Add a `0.25s` padding (`SEGMENT_PADDING_SECONDS`) at the end of each segment's `durationInSeconds` so cuts stay snappy without clipping the last word.
2. **Dynamic Video Length (`remotion-video/src/Root.tsx`):**
   - Use Remotion's `calculateMetadata` function in `<Composition id="DramaCastVideo" ... />` to dynamically sum `segment.durationInFrames` across all segments in `props.segments`, setting the exact total `durationInFrames` of the video automatically.
3. **Visual Design & Animations (`remotion-video/src/Composition.tsx` & Components):**
   - Use `<Series>` from `remotion` to sequence segments one after another cleanly.
   - Inside each `<Series.Sequence>`, render:
     - `<Audio src={staticFile(segment.audioFile)} volume={1.0} />`
     - `<SocialCard />`: Centered in the upper-middle area (`top: 280px`), styled with Tailwind (`bg-slate-900/75 backdrop-blur-xl border border-white/15 rounded-3xl p-8 shadow-2xl text-white`). Animate entry using `spring({ frame, fps, config: { damping: 14 }

## 6. `news` Template (News-Explainer Style)
Reference style: vertical news explainer. Layout at 1080x1920:
- B-roll (stock clip or photo, slow Ken Burns zoom, hard cut per segment) fills `top: 0 -> 1350px`, fading over the last 290px into a solid `brandColor` panel.
- `brandName` watermark at `top: 1095px, left: 48px`, white, 55% opacity, letter-spaced.
- Segment 1 is the hook: narrator reads `topicTitle` while `TitleCard` (white card + offset `brandColor` layer, brand label, red bar, `topicHighlight` in `brandColor`, squiggle) springs in at `top: 1010px`. No captions on segment 1.
- Segments 2+: `NewsSubtitle` shows one phrase at a time (white, bold, 36px, centered, 720px wide, `top: 1215px`); a phrase stays until the next one starts.
- Script (`scriptwriter.py`, Groq by default): 10-16 segments, 1-2 sentences each, plus an English `media_query` per segment for the stock search.
- Pixabay search responses are cached 24h in `backend/.cache/media_search/` (Pixabay terms); source credits are written to `outputs/<jobId>_credits.txt`.
- Phrase grouping (`tts_engine.py`): break after `.!?…`, after `,;:` once the phrase has >= 28 chars, hard cap 90 chars; phrase text is sliced from the original narration so casing and punctuation are kept.- TTS reliability (`tts_engine.py`): Edge TTS intermittently returns no audio for vi-VN voices (rany2/edge-tts#512). Each sentence is synthesized separately (falling back to comma clauses), retried with backoff alternating NFC/NFD text, quotes and CJK stripped from the spoken text, and cached in `backend/.cache/tts/`. A segment that still fails is skipped (except segment 1). Resume a failed job with `python -m app.pipeline --script outputs/<jobId>_script.json`.
- Script checks (`scriptwriter.py`): news scripts need >= 10 segments, a `topic_highlight` substring of the title, and a question in the last segment; leading section labels ("Bối cảnh:") are stripped. Groq 429s are retried after `retry-after`.
## 7. Templates and selection
- Registry: `TEMPLATES` in `backend/app/pipeline.py` (id -> one-line Vietnamese description). `python -m app.pipeline` without `--template` shows a numbered menu; the API exposes `GET /templates` and takes `template` in `POST /jobs`.
- Each template has its own LLM prompt in `scriptwriter.PROMPTS` and minimum segment count in `MIN_SEGMENTS`.
- `story` (reference: Threads story-reading videos): first-person confession, 8-14 paragraphs. Segment 1 narration = `topicTitle`, shown as a Threads post (`authorName` = username, `authorHandle` = community, `likesCount`). Later segments are paragraphs in a dark panel over a looping gameplay clip; the current paragraph appears phrase by phrase from its `subtitles`.
- `techcards` (reference: pastel tech-news motion graphics): every segment carries a `card`; first is `hero`, last is `cta` (follow-the-channel card + question), at least two `media` cards (only these fetch Pixabay media via `media_query`) and one `bullets`/`versus`. Cards blur in with staggered springs and fade out over the last 6 frames.