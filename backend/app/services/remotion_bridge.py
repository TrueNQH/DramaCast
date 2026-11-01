"""Prepares public/current_job/ and shells out to `npx remotion render`."""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path

from app.config import JOB_DIR, OUTPUTS_DIR, PUBLIC_DIR, REMOTION_DIR
from app.schemas import VideoProps


def reset_job_dir() -> Path:
    if JOB_DIR.exists():
        shutil.rmtree(JOB_DIR)
    JOB_DIR.mkdir(parents=True)
    return JOB_DIR


def public_path(path: Path) -> str:
    """Path relative to remotion-video/public, as staticFile() expects."""
    return path.relative_to(PUBLIC_DIR).as_posix()


async def render(props: VideoProps) -> Path:
    props_file = JOB_DIR / "inputProps.json"
    props_file.write_text(props.to_json(), encoding="utf-8")
    OUTPUTS_DIR.mkdir(exist_ok=True)
    out_file = OUTPUTS_DIR / f"{props.job_id}.mp4"

    npx = shutil.which("npx")
    if not npx:
        raise RuntimeError("npx not found: install Node.js 20+")
    cmd = [npx, "remotion", "render", "src/index.ts", "DramaCastVideo", str(out_file), f"--props={props_file}"]
    # subprocess.run in a thread works with every asyncio loop on Windows.
    result = await asyncio.to_thread(
        subprocess.run, cmd, cwd=REMOTION_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        raise RuntimeError(f"Remotion render failed:\n{result.stderr[-4000:]}")
    return out_file
