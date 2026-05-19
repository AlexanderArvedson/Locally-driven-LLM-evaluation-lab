"""
Unit tests for the runtime graph nodes.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from runtime.state import GraphState
from runtime.graph import (
    fetch_context,
    generate,
    verify,
    review,
    route_review,
    route_verify,
    _extract_code_from_response,
    _parse_review_response,
)


@pytest.mark.unit
class TestFetchContextNode:
    """Tests for the fetch_context node."""

    def test_fetch_context_with_optional_context(self):
        """Test fetch_context extracts optional_context."""
        state = GraphState(
            initial_prompt="Refactor this code",
            code_to_refactor="def foo(): pass",
            language="python",
            optional_context="Use best practices",
            context=None,
            generation=None,
            review=None,
            iteration=0,
            max_iterations=3,
            stop_reason=None,
        )

        result = asyncio.run(fetch_context(state))

        assert result["context"] == "Use best practices"

    def test_fetch_context_without_optional_context(self):
        """Test fetch_context handles None optional_context."""
        state = GraphState(
            initial_prompt="Refactor this code",
            code_to_refactor="def foo(): pass",
            language="python",
            optional_context=None,
            context=None,
            generation=None,
            review=None,
            iteration=0,
            max_iterations=3,
            stop_reason=None,
        )

        result = asyncio.run(fetch_context(state))

        assert result["context"] == ""


@pytest.mark.unit
class TestGenerateNode:
    """Tests for the generate node."""

    def test_generate_success(self):
        """Test successful code generation."""
        mock_response = """Here's the refactored code:

```python
def foo_improved():
    return "improved"
```

This code is now clearer."""

        state = GraphState(
            initial_prompt="Refactor this code",
            code_to_refactor="def foo(): pass",
            language="python",
            optional_context=None,
            context="Use best practices",
            generation=None,
            review=None,
            iteration=0,
            max_iterations=3,
            stop_reason=None,
        )

        with patch("runtime.graph.call_ollama", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            result = asyncio.run(generate(state))

        assert result["generation"] is not None
        assert 'return "improved"' in result["generation"]
        assert result["stop_reason"] is None


@pytest.mark.unit
class TestVerifyNode:
    """Tests for the verify node."""

    def test_verify_success(self):
        state = GraphState(
            initial_prompt="Refactor this code",
            code_to_refactor="def foo(): pass",
            language="python",
            optional_context=None,
            context="Use best practices",
            generation="def foo_improved():\n    return 'improved'",
            verification=None,
            review=None,
            iteration=0,
            max_iterations=3,
            stop_reason=None,
        )

        result = asyncio.run(verify(state))

        assert result["verification"]["passed"] is True
        assert result["stop_reason"] is None

    def test_verify_failure(self):
        state = GraphState(
            initial_prompt="Refactor this code",
            code_to_refactor="def foo(): pass",
            language="python",
            optional_context=None,
            context="Use best practices",
            generation="def broken(:\n    pass",
            verification=None,
            review=None,
            iteration=0,
            max_iterations=3,
            stop_reason=None,
        )

        result = asyncio.run(verify(state))

        assert result["verification"]["passed"] is False
        assert "Line" in result["stop_reason"]

    def test_generate_error_handling(self):
        """Test generate node handles errors gracefully."""
        state = GraphState(
            initial_prompt="Refactor this code",
            code_to_refactor="def foo(): pass",
            language="python",
            optional_context=None,
            context=None,
            generation=None,
            review=None,
            iteration=0,
            max_iterations=3,
            stop_reason=None,
        )

        with patch("runtime.graph.call_ollama", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = RuntimeError("API timeout")
            result = asyncio.run(generate(state))

        assert result["generation"] is None
        assert "generation_error" in result["stop_reason"]


@pytest.mark.unit
class TestReviewNode:
    """Tests for the review node."""

    def test_review_approved(self):
        """Test review with approved code."""
        mock_response = """1. Is the refactored code an improvement? Yes
2. Main improvements: Better naming, clearer logic
3. No issues
4. Score: 8/10"""

        state = GraphState(
            initial_prompt="Refactor this code",
            code_to_refactor="def foo(): pass",
            language="python",
            optional_context=None,
            context=None,
            generation="def foo_improved():\n    return 'improved'",
            review=None,
            iteration=1,
            max_iterations=3,
            stop_reason=None,
        )

        with patch("runtime.graph.call_ollama", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            result = asyncio.run(review(state))

        assert result["review"]["approved"] is True
        assert result["review"]["score"] == 8

    def test_review_not_approved(self):
        """Test review with not-approved code."""
        mock_response = """1. Is the refactored code an improvement? No
2. Main issues: Missing error handling, unclear variables
3. Score: 3/10"""

        state = GraphState(
            initial_prompt="Refactor this code",
            code_to_refactor="def foo(): pass",
            language="python",
            optional_context=None,
            context=None,
            generation="def f(): pass",
            review=None,
            iteration=1,
            max_iterations=3,
            stop_reason=None,
        )

        with patch("runtime.graph.call_ollama", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            result = asyncio.run(review(state))

        assert result["review"]["approved"] is False
        assert result["review"]["score"] == 3

    def test_review_no_generated_code(self):
        """Test review when no code was generated."""
        state = GraphState(
            initial_prompt="Refactor this code",
            code_to_refactor="def foo(): pass",
            language="python",
            optional_context=None,
            context=None,
            generation=None,
            review=None,
            iteration=1,
            max_iterations=3,
            stop_reason=None,
        )

        result = asyncio.run(review(state))

        assert result["review"]["approved"] is False
        assert "No code was generated" in result["review"]["feedback"]


@pytest.mark.unit
class TestRouteReview:
    """Tests for the route_review routing function."""

    def test_route_review_approved(self):
        """Test routing when code is approved."""
        state = GraphState(
            initial_prompt="Refactor",
            code_to_refactor="code",
            language="python",
            optional_context=None,
            context=None,
            generation="improved",
            review={"approved": True, "score": 8.0, "feedback": "Good"},
            iteration=1,
            max_iterations=3,
            stop_reason=None,
        )

        from langgraph.graph import END
        result = route_review(state)

        assert result == END


@pytest.mark.unit
class TestRouteVerify:
    """Tests for the route_verify routing function."""

    def test_route_verify_passed(self):
        state = GraphState(
            initial_prompt="Refactor",
            code_to_refactor="code",
            language="python",
            optional_context=None,
            context=None,
            generation="improved",
            verification={"passed": True, "details": {"syntax": "passed"}},
            review=None,
            iteration=1,
            max_iterations=3,
            stop_reason=None,
        )

        assert route_verify(state) == "review"

    def test_route_verify_failed(self):
        state = GraphState(
            initial_prompt="Refactor",
            code_to_refactor="code",
            language="python",
            optional_context=None,
            context=None,
            generation="broken",
            verification={"passed": False, "error_message": "syntax failed"},
            review=None,
            iteration=1,
            max_iterations=3,
            stop_reason=None,
        )

        from langgraph.graph import END

        assert route_verify(state) == END

    def test_route_review_not_approved_continue(self):
        """Test routing continues generation when not approved."""
        state = GraphState(
            initial_prompt="Refactor",
            code_to_refactor="code",
            language="python",
            optional_context=None,
            context=None,
            generation="not_great",
            review={"approved": False, "score": 2.0, "feedback": "Needs work"},
            iteration=1,
            max_iterations=3,
            stop_reason=None,
        )

        result = route_review(state)

        assert result == "generate"

    def test_route_review_max_iterations_reached(self):
        """Test routing stops when max iterations reached."""
        state = GraphState(
            initial_prompt="Refactor",
            code_to_refactor="code",
            language="python",
            optional_context=None,
            context=None,
            generation="code",
            review={"approved": False, "score": 5.0, "feedback": "OK"},
            iteration=3,
            max_iterations=3,
            stop_reason=None,
        )

        from langgraph.graph import END
        result = route_review(state)

        assert result == END
        assert state["stop_reason"] == "max_iterations_reached"


@pytest.mark.unit
class TestCodeExtraction:
    """Tests for code extraction from LLM responses."""

    def test_extract_code_with_language_block(self):
        """Test extracting code from markdown block with language."""
        response = """Here's the refactored code:

```python
def foo():
    return "bar"
```

That's it!"""

        result = _extract_code_from_response(response, "python")

        assert 'def foo():' in result
        assert 'return "bar"' in result

    def test_extract_code_generic_block(self):
        """Test extracting code from generic code block."""
        response = """```
def foo():
    pass
```"""

        result = _extract_code_from_response(response, "python")

        assert "def foo():" in result

    def test_extract_code_no_block(self):
        """Test when code is not in a block."""
        response = """def foo():
    return 42"""

        result = _extract_code_from_response(response, "python")

        assert "def foo():" in result


@pytest.mark.unit
class TestReviewParsing:
    """Tests for parsing review responses."""

    def test_parse_review_with_score(self):
        """Test parsing review with explicit score."""
        response = """Yes, this is better.
Score: 7/10"""

        result = _parse_review_response(response)

        assert result["approved"] is True
        assert result["score"] == 7

    def test_parse_review_no_score(self):
        """Test parsing review without explicit score."""
        response = "No, this is worse."

        result = _parse_review_response(response)

        assert result["approved"] is False
        assert result["score"] == 0.0

    def test_parse_review_ambiguous(self):
        """Test parsing ambiguous review."""
        response = "It might work but needs testing."

        result = _parse_review_response(response)

        # Should default to not approved if no clear yes/no
        assert "might work" in result["feedback"]


@pytest.mark.unit
class TestStateIntegration:
    """Tests for state management across nodes."""

    def test_state_flows_through_nodes(self):
        """Test state flows correctly through nodes."""
        initial_state = GraphState(
            initial_prompt="Make it better",
            code_to_refactor="x = 1",
            language="python",
            optional_context="Use functions",
            context=None,
            generation=None,
            review=None,
            iteration=0,
            max_iterations=3,
            stop_reason=None,
        )

        # Fetch context
        state = asyncio.run(fetch_context(initial_state))
        assert state["context"] == "Use functions"

        # Mock generation
        mock_response = """```python
def get_one():
    return 1
```"""
        with patch("runtime.graph.call_ollama", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            state = asyncio.run(generate(state))

        assert state["generation"] is not None
        assert "get_one" in state["generation"]
