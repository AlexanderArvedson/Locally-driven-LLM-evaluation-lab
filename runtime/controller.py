from __future__ import annotations
import asyncio
from .queue import JobQueue, JobStatus
from .graph import create_graph
from .state import GraphState, RuntimeContext
from .tracing import create_langfuse_trace

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
            
            runtime_context = RuntimeContext(job_id=job.id)
            
            trace = create_langfuse_trace(job.data, runtime_context)
            runtime_context.trace_id = trace.id

            try:
                initial_state = GraphState(
                    initial_prompt=job.data.get("prompt", ""),
                    code_to_refactor=job.data.get("code", ""),
                    context=None,
                    generation=None,
                    review=None,
                    validation_result=None,
                    iteration=0,
                    max_iterations=job.data.get("max_iterations", 5),
                    stop_reason=None,
                )

                # Execute the graph
                final_state = await self.workflow.ainvoke(initial_state)

                job.result = final_state
                job.status = JobStatus.COMPLETED
                trace.update(output=final_state, status='COMPLETED')

            except Exception as e:
                job.result = {"error": str(e)}
                job.status = JobStatus.FAILED
                if trace:
                    trace.update(output={"error": str(e)}, status='ERROR')
            finally:
                self.job_queue.task_done()

    async def start(self):
        """Starts the controller's job processing loop."""
        print("RuntimeController started, waiting for jobs...")
        asyncio.create_task(self.process_jobs())
