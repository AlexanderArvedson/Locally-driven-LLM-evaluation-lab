from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime

from .queue import JobQueue, JobStatus
from .graph import create_graph
from .state import GraphState, RuntimeContext
from .tracing import create_langfuse_trace, create_span

logger = logging.getLogger(__name__)


class RuntimeController:
    """
    Orchestrates the execution of jobs from the queue.
    """

    def __init__(self, job_queue: JobQueue):
        self.job_queue = job_queue
        self.workflow = create_graph()

    async def process_jobs(self):
        """Continuously process jobs from the queue."""
        while True:
            job = await self.job_queue.get()

            runtime_context = RuntimeContext(
                job_id=job.id,
                start_time=datetime.now(),
            )

            trace = create_langfuse_trace(job.data, runtime_context)
            runtime_context.trace_id = trace.id

            try:
                await self._execute_job(job, runtime_context, trace)

            except Exception as e:
                logger.error(f"Unexpected error processing job {job.id}: {str(e)}")
                job.result = {
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
                job.status = JobStatus.FAILED
                try:
                    trace.update(output={"error": str(e)}, status="ERROR")
                except Exception:
                    pass

            finally:
                self.job_queue.task_done()

    async def _execute_job(
        self,
        job,
        runtime_context: RuntimeContext,
        trace,
    ):
        """Execute a single job through the workflow."""
        job.status = JobStatus.RUNNING

        # Extract job input
        job_data = job.data
        prompt = job_data.get("prompt", "")
        code = job_data.get("code_to_refactor", job_data.get("code", ""))
        language = job_data.get("language", "python")
        optional_context = job_data.get("context", None)
        max_iterations = job_data.get("max_iterations", 3)

        runtime_context.language = language

        # Create initial state
        initial_state = GraphState(
            initial_prompt=prompt,
            code_to_refactor=code,
            language=language,
            optional_context=optional_context,
            context=None,
            generation=None,
            review=None,
            iteration=0,
            max_iterations=max_iterations,
            stop_reason=None,
        )

        logger.info(
            f"Starting workflow for job {job.id}: "
            f"language={language}, max_iterations={max_iterations}"
        )

        # Execute the graph
        workflow_start = time.time()
        final_state = await self.workflow.ainvoke(initial_state)
        workflow_duration = time.time() - workflow_start

        # Format job result
        result = self._format_result(
            final_state,
            runtime_context,
            workflow_duration,
        )

        job.result = result
        job.status = JobStatus.COMPLETED

        logger.info(
            f"Job {job.id} completed: "
            f"iterations={final_state['iteration']}, "
            f"duration={workflow_duration:.2f}s, "
            f"stop_reason={final_state['stop_reason']}"
        )

        try:
            trace.update(output=result, status="COMPLETED")
        except Exception:
            pass

    def _format_result(
        self,
        final_state: GraphState,
        runtime_context: RuntimeContext,
        workflow_duration: float,
    ) -> dict:
        """Format the workflow result into a job result."""
        elapsed_time = (
            (datetime.now() - runtime_context.start_time).total_seconds()
            if runtime_context.start_time
            else workflow_duration
        )

        review_data = final_state.get("review") or {}
        stop_reason = final_state.get("stop_reason")

        if not stop_reason:
            if review_data.get("approved"):
                stop_reason = "approved_by_reviewer"
            elif final_state.get("iteration", 0) >= final_state.get("max_iterations", 3):
                stop_reason = "max_iterations_reached"
            elif final_state.get("generation") is None:
                stop_reason = "generation_error"

        result = {
            "generated_code": final_state.get("generation"),
            "review_feedback": review_data.get("feedback"),
            "review_score": review_data.get("score"),
            "approved": review_data.get("approved", False),
            "iterations_used": final_state.get("iteration", 0),
            "stop_reason": stop_reason,
            "total_time_seconds": elapsed_time,
            "language": runtime_context.language,
        }

        if runtime_context.current_model:
            result["model_used"] = runtime_context.current_model

        return result

    async def start(self):
        """Starts the controller's job processing loop."""
        logger.info("RuntimeController started, waiting for jobs...")
        asyncio.create_task(self.process_jobs())

