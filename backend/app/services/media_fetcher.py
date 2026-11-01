"""Finds B-roll for news / techcards segments and the story template's gameplay background.

Sources, in order:
1. Pixabay videos, then Pixabay photos (free key: https://pixabay.com/api/docs/, shown after login)
2. Openverse photos licensed CC0 / public domain (no key needed; opt-in via OPENVERSE_FALLBACK)
3. Local files in remotion-video/public/assets/broll/ (matched by file name)
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from mutagen.mp4 import MP4

from app.config import BACKEND_DIR, GAMEPLAY_DIR, LOCAL_BROLL_DIR, OPENVERSE_FALLBACK, PIXABAY_API_KEY

log = logging.getLogger(__name__)

PIXABAY_VIDEOS = "https://pixabay.com/api/videos/"
PIXABAY_IMAGES = "https://pixabay.com/api/"
OPENVERSE_IMAGES = "https://api.openverse.org/v1/images/"
# Pixabay's terms require caching search responses for 24 hours.
CACHE_DIR = BACKEND_DIR / ".cache" / "media_search"
CACHE_TTL_SECONDS = 24 * 3600
VIDEO_EXTS = {".mp4", ".webm", ".mov"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
# Visually busy, wordless footage for the "story" template background. Avoid ambiguous words:
# "slime" returned a garden slug, "parkour" returns people.
GAMEPLAY_QUERIES = ["kinetic sand", "marble run", "paint pouring", "soap cutting", "acrylic pour"]
GENERIC_WORDS = {
    "close", "up", "closeup", "shot", "view", "aerial", "slow", "motion", "timelapse", "footage",
    "overlay", "illustration", "concept", "of", "a", "an", "the", "in", "on", "with", "and", "vs",
}


@dataclass
class Media:
    path: Path
    media_type: str  # "video" | "image"
    duration_in_seconds: float | None
    credit: str


class MediaFetcher:
    """Keeps track of used items so one job never repeats the same clip."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=60, follow_redirects=True, headers={"User-Agent": "DramaCastStudio/0.1"}
        )
        self._used: set[str] = set()
        self._openverse_blocked = False
        if not PIXABAY_API_KEY:
            log.warning("PIXABAY_API_KEY not set: only %s B-roll", "Openverse + local" if OPENVERSE_FALLBACK else "local")

    async def aclose(self) -> None:
        await self._client.aclose()

    async def fetch(self, query: str, out_stem: Path, min_seconds: float) -> Media | None:
        # Generic camera words dominate stock search ("close up" -> random close-ups), so drop them,
        # then retry with the first two subject words: "moss covered brick" -> "moss covered".
        subject = [w for w in query.lower().split() if w not in GENERIC_WORDS]
        for q in dict.fromkeys([" ".join(subject), " ".join(subject[:2])]):
            if not q:
                continue
            for source in (self._pixabay_video, self._pixabay_image, self._openverse_image):
                try:
                    media = await source(q, out_stem, min_seconds)
                except httpx.HTTPStatusError as exc:
                    log.warning("%s failed for %r: HTTP %s", source.__name__, q, exc.response.status_code)
                    if source == self._openverse_image and exc.response.status_code == 429:
                        self._openverse_blocked = True  # anonymous quota: 20/min, 200/day
                    continue
                except httpx.HTTPError as exc:
                    log.warning("%s failed for %r: %r", source.__name__, q, exc)
                    continue
                if media:
                    return media
        media = self._local(query)
        if not media:
            log.warning("No B-roll found for %r", query)
        return media

    async def fetch_background(self, out_stem: Path, min_seconds: float) -> Media | None:
        """Full-screen looping clip for the "story" template: a random local gameplay clip,
        else a Pixabay clip, preferring portrait and long enough to avoid a visible loop."""
        local = [f for f in GAMEPLAY_DIR.glob("*") if f.suffix.lower() in VIDEO_EXTS] if GAMEPLAY_DIR.exists() else []
        if local:
            clip = random.choice(local)
            return Media(clip, "video", MP4(clip).info.length, f"local: {clip.name}")
        if not PIXABAY_API_KEY:
            return None
        for query in random.sample(GAMEPLAY_QUERIES, len(GAMEPLAY_QUERIES)):
            try:
                data = await self._search(PIXABAY_VIDEOS, {"key": PIXABAY_API_KEY, "q": query, "per_page": 30, "safesearch": "true"})
            except httpx.HTTPError as exc:
                log.warning("gameplay search failed for %r: %r", query, exc)
                continue
            hits = [h for h in data.get("hits", []) if h["videos"].get("medium", {}).get("url")]
            if not hits:
                continue

            def score(h: dict) -> tuple:
                v = h["videos"]["medium"]
                return (v["height"] > v["width"], min(h["duration"], min_seconds), h["duration"])

            hit = max(hits, key=score)
            path = out_stem.with_suffix(".mp4")
            await self._download(hit["videos"]["medium"]["url"], path)
            return Media(path, "video", float(hit["duration"]), f"Pixabay / {hit['user']}: {hit['pageURL']}")
        return None

    async def _pixabay_video(self, query: str, out_stem: Path, min_seconds: float) -> Media | None:
        if not PIXABAY_API_KEY:
            return None
        data = await self._search(PIXABAY_VIDEOS, {"key": PIXABAY_API_KEY, "q": query[:100], "per_page": 20, "safesearch": "true"})
        # Among the most relevant hits, prefer clips long enough to avoid visible looping.
        hits = [h for h in data.get("hits", []) if f"pv{h['id']}" not in self._used][:5]
        hits.sort(key=lambda h: h["duration"] < min_seconds)
        for hit in hits:
            # "medium" is 1920x1080 (or 1280x720 for old clips) and always present; "large" is often 4K.
            rendition = hit["videos"].get("medium") or hit["videos"].get("small")
            if not rendition or not rendition.get("url"):
                continue
            path = out_stem.with_suffix(".mp4")
            await self._download(rendition["url"], path)
            self._used.add(f"pv{hit['id']}")
            return Media(path, "video", float(hit["duration"]), f"Pixabay / {hit['user']}: {hit['pageURL']}")
        return None

    async def _pixabay_image(self, query: str, out_stem: Path, _min_seconds: float) -> Media | None:
        if not PIXABAY_API_KEY:
            return None
        params = {"key": PIXABAY_API_KEY, "q": query[:100], "image_type": "photo", "orientation": "vertical", "per_page": 20, "safesearch": "true"}
        data = await self._search(PIXABAY_IMAGES, params)
        for hit in data.get("hits", []):
            if f"pi{hit['id']}" in self._used:
                continue
            path = out_stem.with_suffix(".jpg")
            await self._download(hit["largeImageURL"], path)
            self._used.add(f"pi{hit['id']}")
            return Media(path, "image", None, f"Pixabay / {hit['user']}: {hit['pageURL']}")
        return None

    async def _openverse_image(self, query: str, out_stem: Path, _min_seconds: float) -> Media | None:
        if self._openverse_blocked or not OPENVERSE_FALLBACK:
            return None
        params = {"q": query, "license": "cc0,pdm", "page_size": 20, "mature": "false"}
        data = await self._search(OPENVERSE_IMAGES, params)
        # Many providers omit dimensions; only drop results known to be too small.
        results = [r for r in data.get("results", []) if (r.get("height") or 900) >= 900]
        for item in results:
            if f"ov{item['id']}" in self._used:
                continue
            path = out_stem.with_suffix(".jpg")
            try:
                await self._download(item["url"], path)
            except httpx.HTTPError:
                continue  # Openverse links point at many third-party hosts; skip dead ones.
            self._used.add(f"ov{item['id']}")
            return Media(path, "image", None, f"Openverse ({item.get('license', 'cc0')}): {item.get('foreign_landing_url', item['url'])}")
        return None

    def _local(self, query: str) -> Media | None:
        if not LOCAL_BROLL_DIR.exists():
            return None
        files = [
            f for f in LOCAL_BROLL_DIR.iterdir()
            if f.suffix.lower() in VIDEO_EXTS | IMAGE_EXTS and f"lf{f.name}" not in self._used
        ]
        if not files:
            return None
        words = set(query.lower().split())
        best = max(files, key=lambda f: (len(words & set(f.stem.lower().replace("-", " ").replace("_", " ").split())), random.random()))
        self._used.add(f"lf{best.name}")
        media_type = "video" if best.suffix.lower() in VIDEO_EXTS else "image"
        # Duration unknown for local clips; BrollMedia then plays the clip once without looping.
        return Media(best, media_type, None, f"local: {best.name}")

    async def _search(self, url: str, params: dict) -> dict:
        public = {k: v for k, v in params.items() if k != "key"}
        key = hashlib.sha1(f"{url}?{json.dumps(public, sort_keys=True)}".encode()).hexdigest()
        cached = CACHE_DIR / f"{key}.json"
        if cached.exists() and time.time() - cached.stat().st_mtime < CACHE_TTL_SECONDS:
            return json.loads(cached.read_text(encoding="utf-8"))
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cached.write_text(resp.text, encoding="utf-8")
        return resp.json()

    async def _download(self, url: str, path: Path) -> None:
        async with self._client.stream("GET", url) as resp:
            resp.raise_for_status()
            with path.open("wb") as f:
                async for chunk in resp.aiter_bytes():
                    f.write(chunk)
