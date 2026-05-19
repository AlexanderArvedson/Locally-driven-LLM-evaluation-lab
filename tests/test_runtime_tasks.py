from __future__ import annotations

from runtime.tasks import RefactoringTask, create_task
from runtime.tasks import DocumentationTask


def test_create_task_defaults_to_refactoring():
    task = create_task()

    assert isinstance(task, RefactoringTask)
    assert task.task_type == "refactoring"


def test_create_task_documentation():
    task = create_task("documentation")

    assert isinstance(task, DocumentationTask)
    assert task.task_type == "documentation"


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


def test_refactoring_task_verification():
    task = RefactoringTask()

    passing = task.verify_generated_code(
        """def improved():
    return True
""",
        "python",
    )
    failing = task.verify_generated_code("def broken(:\n    pass", "python")

    assert passing["passed"] is True
    assert failing["passed"] is False
    assert "Line" in failing["error_message"]


def test_documentation_task_helpers():
    task = DocumentationTask()

    prompt = task.build_generation_prompt(
        code="def foo():\n    return 1",
        language="python",
        context="Add docstrings",
    )

    documented = task.verify_generated_code("def foo():\n    '''Return 1.'''\n    return 1\n", "python")

    missing_docs = task.verify_generated_code(
        "def foo():\n    return 1\n",
        "python",
    )

    assert task.normalize_context(None) == ""
    assert "documentation" in prompt.lower()
    assert documented["passed"] is True
    assert missing_docs["passed"] is False
    assert "docstrings or comments" in missing_docs["error_message"].lower()