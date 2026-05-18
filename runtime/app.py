from __future__ import annotations
import asyncio
from fastapi import FastAPI
from .queue import JobQueue
from .controller import RuntimeController
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI()
job_queue = JobQueue()
controller = RuntimeController(job_queue)

@app.on_event("startup")
async def startup_event():
    """On startup, start the runtime controller."""
    asyncio.create_task(controller.process_jobs())

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
    return {"job_id": job.id, "status": job.status, "result": job.result}
