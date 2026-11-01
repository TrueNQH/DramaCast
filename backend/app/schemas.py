"""Shared data contract. Must stay in sync with remotion-video/src/types/schema.ts."""

from __future__ import annotations

import math
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Platform = Literal["twitter", "reddit", "xiaohongshu", "youtube", "narrator"]
Sentiment = Literal["neutral", "drama", "healing"]
Template = Literal["social", "news", "story", "techcards"]
MediaType = Literal["image", "video"]
CardType = Literal["hero", "media", "bullets", "versus", "quote", "cta"]
Winner = Literal["left", "right", ""]


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class Subtitle(CamelModel):
    text: str
    start_ms: int = Field(alias="startMs")
    end_ms: int = Field(alias="endMs")


class Versus(CamelModel):
    left_label: str = Field("", alias="leftLabel")
    left_text: str = Field("", alias="leftText")
    right_label: str = Field("", alias="rightLabel")
    right_text: str = Field("", alias="rightText")
    winner: Winner = ""


class Card(CamelModel):
    """'techcards' template: what the scene shows (the narration is spoken over it)."""

    type: CardType
    kicker: str = ""  # small pill / media label
    headline: str = ""
    subline: str = ""
    items: list[str] = Field(default_factory=list)  # bullets
    versus: Optional[Versus] = None


class Segment(CamelModel):
    id: int
    platform: Platform = "narrator"
    author_name: str = Field("", alias="authorName")
    author_handle: str = Field("", alias="authorHandle")
    card_content: str = Field("", alias="cardContent", max_length=220)
    likes_count: str = Field("", alias="likesCount")
    sentiment: Sentiment = "neutral"
    audio_file: str = Field(alias="audioFile")
    duration_in_seconds: float = Field(alias="durationInSeconds")
    duration_in_frames: int = Field(alias="durationInFrames")
    subtitles: list[Subtitle] = Field(default_factory=list)
    # "news" template: B-roll shown in the top area of the frame.
    media_file: Optional[str] = Field(None, alias="mediaFile")
    media_type: Optional[MediaType] = Field(None, alias="mediaType")
    media_duration_in_seconds: Optional[float] = Field(None, alias="mediaDurationInSeconds")
    card: Optional[Card] = None


class VideoProps(CamelModel):
    job_id: str = Field(alias="jobId")
    template: Template = "social"
    topic_title: str = Field(alias="topicTitle")
    # Substring of topicTitle rendered in brandColor on the news title card.
    topic_highlight: str = Field("", alias="topicHighlight")
    brand_name: str = Field("DRAMACAST", alias="brandName")
    brand_color: str = Field("#8F1210", alias="brandColor")
    fps: int = 30
    width: int = 1080
    height: int = 1920
    bg_video_file: str = Field("assets/bg_rain_cafe.mp4", alias="bgVideoFile")
    # "story" gameplay background length, used to loop it seamlessly.
    bg_video_duration_in_seconds: Optional[float] = Field(None, alias="bgVideoDurationInSeconds")
    # "techcards" bottom pill, e.g. "threads.net".
    source_label: str = Field("", alias="sourceLabel")
    bgm_audio_file: str = Field("assets/bgm_lofi_chill.mp3", alias="bgmAudioFile")
    bgm_volume: float = Field(0.12, alias="bgmVolume")
    segments: list[Segment]

    def to_json(self) -> str:
        return self.model_dump_json(by_alias=True, indent=2)


def frames_for(seconds: float, fps: int) -> int:
    return math.ceil(seconds * fps)
