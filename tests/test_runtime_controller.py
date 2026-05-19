from __future__ import annotations

from datetime import datetime, timedelta

from runtime.controller import RuntimeController
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
