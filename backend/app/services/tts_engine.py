"""Narration audio + word timestamps grouped into subtitles.

synthesize_all() uses Gemini TTS (see gemini_tts.py) when TTS_ENGINE=gemini and falls back
to per-segment edge-tts.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import logging
import re
import unicodedata
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import edge_tts
import httpx
from mutagen.mp3 import MP3

from app.config import BACKEND_DIR, SEGMENT_PADDING_SECONDS, TTS_ENGINE, TTS_PITCH, TTS_RATE, TTS_VOICE
from app.schemas import Subtitle

log = logging.getLogger(__name__)

TICKS_PER_MS = 10_000  # edge-tts offsets are in 100ns units
RETRY_BACKOFF_SECONDS = (2, 4, 8, 15, 30)
# Sentences that synthesized once are reused, so a rerun after a failure only redoes the rest.
TTS_CACHE_DIR = BACKEND_DIR / ".cache" / "tts"
# Split after sentence / clause punctuation, keeping the punctuation with the left part.
SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+")
CLAUSE_SPLIT = re.compile(r"(?<=[,;:])\s+")
# Quote marks are only visual, and a Vietnamese voice cannot read CJK script; the service
# returns no audio for some inputs containing either, so they are dropped from the spoken text.
TTS_STRIP = re.compile(r"[“”\"«»„⺀-鿿가-힯＀-￯]+")
# Captions run 1-3 lines: always break after a sentence, after a comma once the
# phrase is long enough, and never let a phrase exceed MAX_PHRASE_CHARS.
SENTENCE_END = re.compile(r"[.!?…]")
CLAUSE_END = re.compile(r"[,;:]")
MIN_CLAUSE_CHARS = 28
MAX_PHRASE_CHARS = 90

SubtitleMode = Literal["word", "phrase"]
# Pause between requests; bursts make the service start returning empty audio.
REQUEST_GAP_SECONDS = 0.4


class TtsUnavailable(RuntimeError):
    """The Edge TTS service kept returning no audio for a piece of text."""


@dataclass
class Word:
    text: str
    start_ms: int
    end_ms: int
    span: tuple[int, int] | None = None  # position in the narration, incl. trailing punctuation


@dataclass
class TtsResult:
    audio_path: Path
    duration_in_seconds: float
    subtitles: list[Subtitle]


async def synthesize(text: str, out_path: Path, mode: SubtitleMode = "phrase", voice: str = TTS_VOICE) -> TtsResult:
    text = unicodedata.normalize("NFC", text)
    audio = bytearray()
    words: list[Word] = []
    # Edge TTS intermittently returns no audio, more often for long inputs, so each
    # sentence is synthesized separately and the MP3 frames are concatenated.
    for piece in _split(text, SENTENCE_SPLIT):
        offset_ms = round(_mp3_seconds(bytes(audio)) * 1000) if audio else 0
        chunk_audio, chunk_words = await _synthesize_piece(piece, voice)
        audio += chunk_audio
        words += [Word(w.text, w.start_ms + offset_ms, w.end_ms + offset_ms) for w in chunk_words]
    out_path.write_bytes(audio)

    duration = MP3(out_path).info.length + SEGMENT_PADDING_SECONDS
    return TtsResult(out_path, round(duration, 3), _subtitles(text, words, mode))


async def synthesize_all(narrations: list[str], out_dir: Path, mode: SubtitleMode = "phrase") -> list[TtsResult | None]:
    """One result per narration; None marks a segment whose audio could not be produced."""
    if TTS_ENGINE == "gemini":
        from app.services import gemini_tts

        try:
            parts = await gemini_tts.synthesize_script(narrations, out_dir)
        except (RuntimeError, httpx.HTTPError, wave.Error) as exc:
            log.warning("Gemini TTS unavailable (%s); falling back to edge-tts", exc)
        else:
            # The cut already sits in the pause between segments, so no extra padding.
            return [
                TtsResult(path, duration, _subtitles(text, [Word(t.text, t.start_ms, t.end_ms) for t in tokens], mode))
                for text, (path, duration, tokens) in zip(narrations, parts)
            ]

    results: list[TtsResult | None] = []
    for i, text in enumerate(narrations, start=1):
        try:
            results.append(await synthesize(text, out_dir / f"seg_{i}.mp3", mode))
        except TtsUnavailable:
            if i == 1:
                raise  # the hook carries the title card; no video without it
            log.warning("skipping segment %d: TTS kept failing", i)
            results.append(None)
    return results


def _subtitles(text: str, words: list[Word], mode: SubtitleMode) -> list[Subtitle]:
    if mode == "word":
        return [Subtitle(text=w.text, startMs=w.start_ms, endMs=w.end_ms) for w in words]
    return _group_phrases(unicodedata.normalize("NFC", text), words)


async def _synthesize_piece(text: str, voice: str) -> tuple[bytes, list[Word]]:
    """Retries one sentence, alternating NFC/NFD (either form sometimes gets through);
    if it keeps failing, falls back to synthesizing its comma-separated clauses one by one."""
    spoken = " ".join(TTS_STRIP.sub(" ", text).split())
    if not any(ch.isalnum() for ch in spoken):
        return b"", []
    cached = _cache_get(spoken, voice)
    if cached:
        return cached
    variants = [unicodedata.normalize("NFC", spoken), unicodedata.normalize("NFD", spoken)]
    # Failures come in bursts (rany2/edge-tts#512), so back off for up to about a minute.
    for attempt, backoff in enumerate([*RETRY_BACKOFF_SECONDS, None], start=1):
        try:
            result = await _stream(variants[attempt % 2], voice)
            _cache_put(spoken, voice, result)
            return result
        except edge_tts.exceptions.NoAudioReceived:
            log.warning("edge-tts returned no audio (attempt %d): %s", attempt, text[:60])
            if backoff:
                await asyncio.sleep(backoff)

    clauses = _split(text, CLAUSE_SPLIT)
    if len(clauses) < 2:
        raise TtsUnavailable(f"edge-tts kept returning no audio for: {text}")
    audio = bytearray()
    words: list[Word] = []
    for clause in clauses:
        offset_ms = round(_mp3_seconds(bytes(audio)) * 1000) if audio else 0
        clause_audio, clause_words = await _synthesize_piece(clause, voice)
        audio += clause_audio
        words += [Word(w.text, w.start_ms + offset_ms, w.end_ms + offset_ms) for w in clause_words]
    return bytes(audio), words


async def _stream(text: str, voice: str) -> tuple[bytes, list[Word]]:
    await asyncio.sleep(REQUEST_GAP_SECONDS)
    communicate = edge_tts.Communicate(text, voice=voice, rate=TTS_RATE, pitch=TTS_PITCH, boundary="WordBoundary")
    audio = bytearray()
    words: list[Word] = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio += chunk["data"]
        elif chunk["type"] == "WordBoundary":
            start = chunk["offset"] // TICKS_PER_MS
            # NFD requests come back decomposed; captions are aligned against NFC text.
            word = unicodedata.normalize("NFC", chunk["text"])
            words.append(Word(word, start, start + chunk["duration"] // TICKS_PER_MS))
    return bytes(audio), words


def _cache_key(spoken: str, voice: str) -> Path:
    key = hashlib.sha1(f"{voice}|{TTS_RATE}|{TTS_PITCH}|{spoken}".encode()).hexdigest()
    return TTS_CACHE_DIR / key


def _cache_get(spoken: str, voice: str) -> tuple[bytes, list[Word]] | None:
    base = _cache_key(spoken, voice)
    mp3, meta = base.with_suffix(".mp3"), base.with_suffix(".json")
    if not (mp3.exists() and meta.exists()):
        return None
    words = [Word(w["text"], w["start_ms"], w["end_ms"]) for w in json.loads(meta.read_text(encoding="utf-8"))]
    return mp3.read_bytes(), words


def _cache_put(spoken: str, voice: str, result: tuple[bytes, list[Word]]) -> None:
    audio, words = result
    base = _cache_key(spoken, voice)
    TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    base.with_suffix(".mp3").write_bytes(audio)
    meta = [{"text": w.text, "start_ms": w.start_ms, "end_ms": w.end_ms} for w in words]
    base.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")


def _split(text: str, pattern: re.Pattern[str]) -> list[str]:
    return [p.strip() for p in pattern.split(text) if p.strip()]


def _mp3_seconds(data: bytes) -> float:
    return MP3(io.BytesIO(data)).info.length


def _align(text: str, words: list[Word]) -> None:
    """Locate each spoken word in the original text so phrases keep its casing and punctuation."""
    lower = text.lower()
    cursor = 0
    for w in words:
        at = lower.find(w.text.lower(), cursor)
        if at < 0:
            continue
        end = at + len(w.text)
        while end < len(text) and not text[end].isspace() and not text[end].isalnum():
            end += 1
        w.span = (at, end)
        cursor = end


def _group_phrases(text: str, words: list[Word]) -> list[Subtitle]:
    _align(text, words)

    # First split at punctuation, then cut over-long clauses into near-equal parts so a
    # long sentence doesn't leave a one-word tail ("... nộp | hồ sơ.").
    clauses: list[list[Word]] = []
    group: list[Word] = []
    for w in words:
        group.append(w)
        spoken = text[w.span[0]:w.span[1]] if w.span else w.text
        if SENTENCE_END.search(spoken) or (CLAUSE_END.search(spoken) and _chars(group) >= MIN_CLAUSE_CHARS):
            clauses.append(group)
            group = []
    if group:
        clauses.append(group)

    phrases: list[Subtitle] = []
    for clause in clauses:
        for part in _balanced_parts(clause):
            spans = [w.span for w in part if w.span]
            phrase = text[spans[0][0]:spans[-1][1]].strip() if spans else " ".join(w.text for w in part)
            phrases.append(Subtitle(text=phrase, startMs=max(0, part[0].start_ms), endMs=max(0, part[-1].end_ms)))
    return phrases


def _chars(group: list[Word]) -> int:
    return sum(len(w.text) + 1 for w in group)


def _balanced_parts(clause: list[Word]) -> list[list[Word]]:
    n = -(-_chars(clause) // MAX_PHRASE_CHARS)  # ceil
    if n <= 1:
        return [clause]
    target = _chars(clause) / n
    parts: list[list[Word]] = [[]]
    for w in clause:
        if _chars(parts[-1]) + (len(w.text) + 1) / 2 > target and len(parts) < n:
            parts.append([])
        parts[-1].append(w)
    return [p for p in parts if p]
