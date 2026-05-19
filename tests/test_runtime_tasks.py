from __future__ import annotations

from runtime.tasks import RefactoringTask, create_task


def test_create_task_defaults_to_refactoring():
    task = create_task()

    assert isinstance(task, RefactoringTask)
    assert task.task_type == "refactoring"


def test_refactoring_task_helpers():
    task = RefactoringTask()

    assert task.normalize_context(None) == ""
    assert task.normalize_context("Use clear names") == "Use clear names"

    generated_code = task.extract_generated_code(
        """Here is the result:

```python
def improved():
    return True
```
""",
        "python",
    )
    assert "def improved()" in generated_code

    review = task.parse_review_response(
        """1. Yes
2. Better naming
3. No issues
4. Score: 9/10"""
    )

    assert review["approved"] is True
    assert review["score"] == 9