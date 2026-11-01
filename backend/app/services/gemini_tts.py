"""Whole-script Gemini TTS, split into per-segment WAVs using Groq Whisper word timings.

One TTS request per video keeps within the free tier's small daily request quota. Gemini
does not return timestamps, so the audio is transcribed with word timestamps and aligned
back to the script; captions keep the script's own spelling, only the timing comes from
Whisper. Segments are cut in the middle of the pause between them.
"""

from __future__ import annotations

import base64
import difflib
import hashlib
import io
import json
import logging
import re
import unicodedata
import wave
from pathlib import Path

import httpx

from app.config import (
    BACKEND_DIR,
    GEMINI_API_KEY,
    GEMINI_TTS_MODEL,
    GEMINI_TTS_STYLE,
    GEMINI_TTS_VOICE,
    GROQ_API_KEY,
    WHISPER_MODEL,
)

log = logging.getLogger(__name__)

INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
TRANSCRIBE_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
CACHE_DIR = BACKEND_DIR / ".cache" / "gemini_tts"
SEGMENT_BREAK = " <short pause> "
MIN_SEGMENT_MS = 300  # anything shorter means the alignment went wrong
TOKEN_STRIP = re.compile(r"^[^\w]+|[^\w]+$")


class Timed:
    """A script word with its position in the narration and its time in the audio."""

    def __init__(self, text: str, span: tuple[int, int]) -> None:
        self.text = text
        self.span = span
        self.start_ms: int | None = None
        self.end_ms: int | None = None


async def synthesize_script(narrations: list[str], out_dir: Path) -> list[tuple[Path, float, list[Timed]]]:
    """Returns, per narration, (wav path, duration in seconds, words timed relative to that wav)."""
    if not GEMINI_API_KEY or not GROQ_API_KEY:
        raise RuntimeError("GEMINI_API_KEY and GROQ_API_KEY are both required for TTS_ENGINE=gemini")
    narrations = [unicodedata.normalize("NFC", n) for n in narrations]
    async with httpx.AsyncClient(timeout=300) as client:
        audio = await _tts(client, SEGMENT_BREAK.join(narrations))
        words = await _transcribe(client, audio)

    per_segment = [_tokenize(n) for n in narrations]
    flat = [t for seg in per_segment for t in seg]
    _assign_times(flat, words)

    with wave.open(io.BytesIO(audio)) as w:
        params, rate, frames = w.getparams(), w.getframerate(), w.readframes(w.getnframes())
    bytes_per_ms = rate * params.sampwidth * params.nchannels / 1000
    total_ms = int(len(frames) / bytes_per_ms)

    # Cut points: halfway between one segment's last word and the next segment's first word.
    cuts = [0]
    for prev, nxt in zip(per_segment, per_segment[1:]):
        cut = (prev[-1].end_ms + nxt[0].start_ms) // 2 if prev and nxt else cuts[-1]
        cuts.append(min(max(cuts[-1], cut), total_ms))
    cuts.append(total_ms)
    if any(b - a < MIN_SEGMENT_MS for a, b in zip(cuts, cuts[1:])):
        raise RuntimeError(f"alignment produced a segment shorter than {MIN_SEGMENT_MS} ms: cuts={cuts}")

    results = []
    for i, tokens in enumerate(per_segment):
        start, end = cuts[i], cuts[i + 1]
        frame_bytes = params.sampwidth * params.nchannels
        a = int(start * bytes_per_ms) // frame_bytes * frame_bytes
        b = int(end * bytes_per_ms) // frame_bytes * frame_bytes
        path = out_dir / f"seg_{i + 1}.wav"
        with wave.open(str(path), "wb") as out:
            out.setparams(params)
            out.writeframes(frames[a:b])
        for t in tokens:
            t.start_ms -= start
            t.end_ms -= start
        results.append((path, round((end - start) / 1000, 3), tokens))
    return results


async def _tts(client: httpx.AsyncClient, transcript: str) -> bytes:
    key = hashlib.sha1(f"{GEMINI_TTS_MODEL}|{GEMINI_TTS_VOICE}|{GEMINI_TTS_STYLE}|{transcript}".encode()).hexdigest()
    cached = CACHE_DIR / f"{key}.wav"
    if cached.exists():
        return cached.read_bytes()

    body = {
        "model": GEMINI_TTS_MODEL,
        "input": [{
            "type": "user_input",
            "content": [{
                "type": "text",
                "text": transcript,
                "annotations": [{"type": "speech_metadata", "style": GEMINI_TTS_STYLE}],
            }],
        }],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": GEMINI_TTS_VOICE}]},
    }
    resp = await client.post(INTERACTIONS_URL, headers={"x-goog-api-key": GEMINI_API_KEY}, json=body)
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini TTS HTTP {resp.status_code}: {resp.text[:300]}")
    audio_blocks = [
        c["data"]
        for step in resp.json().get("steps", [])
        if step.get("type") == "model_output"
        for c in step.get("content", [])
        if c.get("type") == "audio"
    ]
    if not audio_blocks:
        raise RuntimeError("Gemini TTS returned no audio")
    audio = base64.b64decode(audio_blocks[-1])
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(audio)
    return audio


async def _transcribe(client: httpx.AsyncClient, audio: bytes) -> list[dict]:
    key = hashlib.sha1(f"{WHISPER_MODEL}|".encode() + audio).hexdigest()
    cached = CACHE_DIR / f"{key}.words.json"
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))

    # A dict, not a list of pairs: httpx's AsyncClient rejects list-form data alongside files.
    # No "prompt": passing the script's opening as a hint made Whisper skip those lines and
    # return stretched timestamps; the alignment step copes with misheard words instead.
    data = {
        "model": WHISPER_MODEL,
        "language": "vi",
        "response_format": "verbose_json",
        "timestamp_granularities[]": "word",
    }
    resp = await client.post(
        TRANSCRIBE_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        data=data,
        files={"file": ("speech.wav", audio, "audio/wav")},
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Groq Whisper HTTP {resp.status_code}: {resp.text[:300]}")
    words = resp.json().get("words", [])
    if not words:
        raise RuntimeError("Groq Whisper returned no word timestamps")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
    return words


def _norm(word: str) -> str:
    return TOKEN_STRIP.sub("", unicodedata.normalize("NFC", word).lower())


def _tokenize(narration: str) -> list[Timed]:
    tokens = []
    for m in re.finditer(r"\S+", narration):
        if _norm(m.group()):
            # Span covers trailing punctuation so phrase grouping can see sentence ends.
            tokens.append(Timed(TOKEN_STRIP.sub("", m.group()) or m.group(), (m.start(), m.end())))
    return tokens


def _assign_times(tokens: list[Timed], words: list[dict]) -> None:
    """Align script tokens to Whisper words; interpolate tokens Whisper heard differently."""
    heard = [_norm(w["word"]) for w in words]
    matcher = difflib.SequenceMatcher(None, [_norm(t.text) for t in tokens], heard, autojunk=False)
    for block in matcher.get_matching_blocks():
        for k in range(block.size):
            w = words[block.b + k]
            tokens[block.a + k].start_ms = round(w["start"] * 1000)
            tokens[block.a + k].end_ms = round(w["end"] * 1000)

    known = [i for i, t in enumerate(tokens) if t.start_ms is not None]
    if not known:
        raise RuntimeError("could not align any script word to the transcription")
    for i, t in enumerate(tokens):
        if t.start_ms is not None:
            continue
        before = max((k for k in known if k < i), default=None)
        after = min((k for k in known if k > i), default=None)
        lo = tokens[before].end_ms if before is not None else 0
        hi = tokens[after].start_ms if after is not None else lo + 400 * (i - before)
        lo_i = before if before is not None else -1
        hi_i = after if after is not None else len(tokens)
        # Spread unmatched words evenly across the gap between their matched neighbours.
        frac = (i - lo_i) / (hi_i - lo_i)
        width = (hi - lo) / (hi_i - lo_i)
        t.start_ms = round(lo + (hi - lo) * frac - width)
        t.end_ms = round(lo + (hi - lo) * frac)
    for t in tokens:
        t.start_ms = max(0, t.start_ms)
        t.end_ms = max(t.start_ms, t.end_ms)
