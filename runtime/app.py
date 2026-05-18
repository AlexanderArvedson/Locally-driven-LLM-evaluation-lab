from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from dotenv import load_dotenv

from .queue import JobQueue
from .controller import RuntimeController

# Load environment variables from .env file
load_dotenv()

job_queue = JobQueue()
controller = RuntimeController(job_queue)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    controller_task = asyncio.create_task(controller.process_jobs())

    try:
        yield
    finally:
        # shutdown: cancel background task cleanly
        controller_task.cancel()
        try:
            await controller_task
        except asyncio.CancelledError:
            pass


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"status": "ok"}


@app.post("/jobs/")
async def create_job(data: dict):
    """Endpoint to create a new job."""
    job = await job_queue.put(data)
    return {"job_id": job.id}


@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Endpoint to get the status of a job."""
    job = job_queue.get_job(job_id)
    if not job:
        return {"error": "Job not found"}
    return {
        "job_id": job.id,
        "status": job.status.value,
        "result": job.result
    }