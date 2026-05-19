from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import asyncio

from runtime.controller import RuntimeController
from runtime.queue import Job
from runtime.queue import JobQueue
from runtime.state import GraphState, RuntimeContext


def test_format_result_infers_stop_reason_and_elapsed_time():
    controller = RuntimeController(JobQueue())

    final_state = GraphState(
        initial_prompt="Test",
        code_to_refactor="old code",
        language="python",
        optional_context=None,
        context=None,
        generation="new code",
        review={"approved": True, "feedback": "Good", "score": 9},
        iteration=1,
        max_iterations=3,
        stop_reason=None,
    )

    runtime_context = RuntimeContext(
        language="python",
        start_time=datetime.now() - timedelta(seconds=2),
    )

    result = controller._format_result(final_state, runtime_context, workflow_duration=2.0)

    assert result["stop_reason"] == "approved_by_reviewer"
    assert result["total_time_seconds"] > 0
    assert result["review_score"] == 9
    assert result["approved"] is True


def test_controller_can_run_documentation_task():
    controller = RuntimeController(JobQueue())
    job = Job(
        data={
            "task_type": "documentation",
            "prompt": "Add docstrings",
            "code_to_refactor": "def foo():\n    return 1\n",
            "language": "python",
            "context": "Document public functions",
            "max_iterations": 1,
        }
    )

    runtime_context = RuntimeContext(
        job_id=job.id,
        task_type="documentation",
        language="python",
        start_time=datetime.now() - timedelta(seconds=1),
    )

    trace = MagicMock()
    trace.id = "trace-doc"
    trace.update = MagicMock()

    with patch("runtime.graph.call_ollama", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = [
            """```python
def foo():
    '''Return 1.'''
    return 1
```""",
            """1. Yes
2. Clear docstrings
3. No issues
4. Score: 9/10""",
        ]

        asyncio.run(controller._execute_job(job, runtime_context, trace))

    assert job.status.value == "completed"
    assert job.result["task_type"] == "documentation"
    assert job.result["verification"]["passed"] is True
    assert job.result["review_score"] == 9
