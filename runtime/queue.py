from __future__ import annotations

import asyncio
from enum import Enum
from dataclasses import dataclass, field
import uuid
from typing import Any, Dict

class JobStatus(str, Enum):
    """Enumeration for job status."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Job:
    """Represents a job in the queue."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.QUEUED
    data: Dict[str, Any] = field(default_factory=dict)
    result: Any = None

class JobQueue:
    """A simple in-memory job queue."""
    def __init__(self):
        self._queue = asyncio.Queue()
        self._jobs: Dict[str, Job] = {}

    async def put(self, job_data: Dict[str, Any]) -> Job:
        """Adds a new job to the queue."""
        job = Job(data=job_data)
        self._jobs[job.id] = job
        await self._queue.put(job)
        return job

    async def get(self) -> Job:
        """Retrieves the next job from the queue."""
        job = await self._queue.get()
        job.status = JobStatus.RUNNING
        return job

    def get_job(self, job_id: str) -> Job | None:
        """Gets a job by its ID."""
        return self._jobs.get(job_id)

    def task_done(self):
        """Marks a task as done."""
        self._queue.task_done()
