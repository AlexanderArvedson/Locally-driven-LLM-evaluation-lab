"""
Integration tests for the runtime workflow.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from runtime.graph import create_graph
from runtime.state import GraphState


@pytest.mark.integration
class TestGraphCompilation:
    """Tests for graph creation and compilation."""

    def test_graph_compiles_successfully(self):
        """Test that the graph compiles without errors."""
        graph = create_graph()
        assert graph is not None

    def test_graph_executes_with_mock_data(self):
        """Test graph can be invoked with complete state."""
        graph = create_graph()

        initial_state = GraphState(
            initial_prompt="Test prompt",
            code_to_refactor="def test(): pass",
            language="python",
            optional_context=None,
            context=None,
            generation=None,
            review=None,
            iteration=0,
            max_iterations=1,
            stop_reason=None,
        )

        with patch("runtime.graph.call_ollama", new_callable=AsyncMock) as mock_llm:
            # Mock generation response
            mock_llm.side_effect = [
                "```python\ndef test(): return True\n```",  # generation
                "1. Yes\n2. Good\n3. Score: 9/10",  # review (approved)
            ]

            result = asyncio.run(graph.ainvoke(initial_state))

        assert result is not None
        assert result["generation"] is not None
        assert result["review"]["approved"] is True
        assert result["iteration"] == 1  # Iteration incremented by review node


@pytest.mark.integration
class TestEndToEndWorkflow:
    """End-to-end workflow tests using graph directly."""

    def test_full_workflow_single_pass(self):
        """Test complete workflow that gets approved on first iteration."""
        graph = create_graph()

        initial_state = GraphState(
            initial_prompt="Refactor for clarity",
            code_to_refactor="x=1;y=2",
            language="python",
            optional_context="Use clear variable names",
            context=None,
            generation=None,
            review=None,
            iteration=0,
            max_iterations=3,
            stop_reason=None,
        )

        with patch("runtime.graph.call_ollama", new_callable=AsyncMock) as mock_llm:
            generation_response = """```python
x = 1
y = 2
```"""
            review_response = """1. Yes
2. Clearer
3. No issues
4. Score: 9/10"""
            
            mock_llm.side_effect = [generation_response, review_response]

            result = asyncio.run(graph.ainvoke(initial_state))

        assert result["generation"] is not None
        assert "x = 1" in result["generation"]
        assert result["review"]["approved"] is True
        assert result["iteration"] == 1

    def test_full_workflow_multiple_iterations(self):
        """Test workflow loops until code is approved."""
        graph = create_graph()

        initial_state = GraphState(
            initial_prompt="Improve code",
            code_to_refactor="def f():pass",
            language="python",
            optional_context=None,
            context=None,
            generation=None,
            review=None,
            iteration=0,
            max_iterations=2,
            stop_reason=None,
        )

        with patch("runtime.graph.call_ollama", new_callable=AsyncMock) as mock_llm:
            generation_response = "```python\ndef improved():\n    pass\n```"
            review_rejected = "1. No\n2. Not enough\n3. Score: 4/10"
            review_approved = "1. Yes\n2. Great!\n3. Score: 8/10"
            
            mock_llm.side_effect = [
                generation_response,  # First generation
                review_rejected,      # First review rejects
                generation_response,  # Second generation
                review_approved,      # Second review approves
            ]

            result = asyncio.run(graph.ainvoke(initial_state))

        assert result["generation"] is not None
        assert result["review"]["approved"] is True
        assert result["iteration"] == 2

    def test_workflow_stops_at_max_iterations(self):
        """Test workflow stops when max iterations reached."""
        graph = create_graph()

        initial_state = GraphState(
            initial_prompt="Improve code",
            code_to_refactor="code",
            language="python",
            optional_context=None,
            context=None,
            generation=None,
            review=None,
            iteration=0,
            max_iterations=1,
            stop_reason=None,
        )

        with patch("runtime.graph.call_ollama", new_callable=AsyncMock) as mock_llm:
            generation_response = "```python\ncode\n```"
            review_rejected = "1. No\n2. Bad\n3. Score: 2/10"
            
            mock_llm.side_effect = [
                generation_response,  # 1st generation
                review_rejected,      # 1st review rejects (hits max iterations after this)
            ]

            result = asyncio.run(graph.ainvoke(initial_state))

        assert result["generation"] is not None
        assert result["review"]["approved"] is False
        assert result["iteration"] == 1

