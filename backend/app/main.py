"""FastAPI entry point. Run: uvicorn app.main:app --reload (from backend/)."""

from __future__ import annotations

import asyncio
import uuid
from typing import Literal, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

from app.pipeline import TEMPLATES, run_job
from app.schemas import Template

app = FastAPI(title="DramaCast Studio")

# public/current_job/ is shared, so jobs render one at a time.
_render_lock = asyncio.Lock()
_jobs: dict[str, "JobStatus"] = {}


class JobRequest(BaseModel):
    topic: str = ""
    template: Template = "news"
    use_mock: bool = False
    brand_name: str = "DRAMACAST"
    brand_color: str = "#8F1210"


class JobStatus(BaseModel):
    job_id: str
    status: Literal["queued", "running", "done", "failed"]
    stage: str = ""
    output_file: Optional[str] = None
    error: Optional[str] = None


async def _run(job: JobStatus, req: JobRequest) -> None:
    async with _render_lock:
        job.status = "running"
        try:
            out = await run_job(
                req.topic,
                req.template,
                job_id=job.job_id,
                use_mock=req.use_mock,
                brand_name=req.brand_name,
                brand_color=req.brand_color,
                on_progress=lambda stage: setattr(job, "stage", stage),
            )
            job.status, job.output_file = "done", str(out)
        except Exception as exc:  # surfaced through GET /jobs/{id}
            job.status, job.error = "failed", str(exc)


@app.get("/templates")
async def list_templates() -> dict[str, str]:
    """Template ids accepted by POST /jobs, with a one-line description each."""
    return TEMPLATES


@app.post("/jobs", response_model=JobStatus)
async def create_job(req: JobRequest, background: BackgroundTasks) -> JobStatus:
    job = JobStatus(job_id=uuid.uuid4().hex[:10], status="queued")
    _jobs[job.job_id] = job
    background.add_task(_run, job, req)
    return job


@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job(job_id: str) -> JobStatus:
    if job_id not in _jobs:
        raise HTTPException(404, "job not found")
    return _jobs[job_id]
