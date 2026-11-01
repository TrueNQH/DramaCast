"""Agent-Reach CLI wrapper with a mock-data fallback."""

from __future__ import annotations

import json
import logging
import shlex
import subprocess
from pathlib import Path

from pydantic import BaseModel

from app.config import AGENT_REACH_CMD, MOCK_DATA_FILE

log = logging.getLogger(__name__)


class RawPost(BaseModel):
    platform: str
    author_name: str = ""
    author_handle: str = ""
    content: str
    likes: str = ""
    top_comments: list[str] = []


def fetch_posts(query: str, use_mock: bool = False, mock_file: Path | None = None) -> list[RawPost]:
    if not use_mock and not mock_file and AGENT_REACH_CMD:
        try:
            return _run_agent_reach(query)
        except (subprocess.SubprocessError, OSError, ValueError) as exc:
            log.warning("Agent-Reach failed (%s); falling back to mock data", exc)
    return _load_mock(mock_file or MOCK_DATA_FILE)


def _run_agent_reach(query: str) -> list[RawPost]:
    args = [a.replace("{query}", query) for a in shlex.split(AGENT_REACH_CMD, posix=False)]
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", timeout=300, check=True)
    data = json.loads(result.stdout)
    posts = [RawPost.model_validate(item) for item in (data["posts"] if isinstance(data, dict) else data)]
    if not posts:
        raise ValueError("Agent-Reach returned no posts")
    return posts


def _load_mock(path: Path) -> list[RawPost]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [RawPost.model_validate(item) for item in data]
