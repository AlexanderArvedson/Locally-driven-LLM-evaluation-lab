"""Runtime workflow graph for maintenance tasks.

This module builds a small LangGraph StateGraph that runs the
fetch → generate → verify → review loop. Tasks provide the
task-specific prompts, extraction and verification helpers.
"""

from __future__ import annotations

import logging
from langgraph.graph import StateGraph, END
from .state import GraphState
from .llm import call_ollama
from .tasks import RuntimeTask, create_task

logger = logging.getLogger(__name__)

# Default task used by the module-level helper wrappers (primarily for tests)
DEFAULT_TASK = create_task()


async def _fetch_context(state: GraphState, task: RuntimeTask) -> GraphState:
    logger.info("---FETCHING CONTEXT---")

    state["context"] = task.normalize_context(state.get("optional_context"))

    return state


async def _generate(state: GraphState, task: RuntimeTask) -> GraphState:
    logger.info("---GENERATING CODE---")

    try:
        prompt = task.build_generation_prompt(
            code=state["code_to_refactor"],
            language=state["language"],
            context=state.get("context") or "",
        )

        logger.debug(f"Calling LLM for generation (iteration {state['iteration']})")

        response = await call_ollama(prompt)

        generated_code = task.extract_generated_code(response, state["language"])

        state["generation"] = generated_code
        logger.debug(f"Generated code: {len(generated_code)} chars")

    except Exception as e:
        logger.error(f"Error during code generation: {str(e)}")
        state["generation"] = None
        state["stop_reason"] = f"generation_error: {str(e)}"

    return state


async def _verify(state: GraphState, task: RuntimeTask) -> GraphState:
    logger.info("---VERIFYING CODE---")

    generated_code = state.get("generation") or ""
    verification = task.verify_generated_code(generated_code, state["language"])
    state["verification"] = verification

    if not verification.get("passed", False):
        state["stop_reason"] = verification.get("error_message") or "verification_failed"

    return state


async def _review(state: GraphState, task: RuntimeTask) -> GraphState:
    logger.info("---REVIEWING CODE---")

    state["iteration"] = state.get("iteration", 0) + 1

    if state.get("generation") is None:
        logger.warning("No generated code to review")
        state["review"] = {
            "approved": False,
            "feedback": "No code was generated",
            "score": 0.0,
        }
        return state

    try:
        prompt = task.build_review_prompt(
            original_code=state["code_to_refactor"],
            generated_code=state["generation"],
            language=state["language"],
            context=state.get("context") or "",
        )

        logger.debug("Calling LLM for review")

        response = await call_ollama(prompt)

        review_data = task.parse_review_response(response)

        state["review"] = review_data
        logger.debug(f"Review score: {review_data.get('score', 'N/A')}")

    except Exception as e:
        logger.error(f"Error during code review: {str(e)}")
        state["review"] = {
            "approved": False,
            "feedback": f"Review failed: {str(e)}",
            "score": 0.0,
        }

    return state


async def fetch_context(state: GraphState) -> GraphState:
    return await _fetch_context(state, DEFAULT_TASK)


async def generate(state: GraphState) -> GraphState:
    return await _generate(state, DEFAULT_TASK)


async def verify(state: GraphState) -> GraphState:
    return await _verify(state, DEFAULT_TASK)


async def review(state: GraphState) -> GraphState:
    return await _review(state, DEFAULT_TASK)


def _extract_code_from_response(response: str, language: str) -> str:
    return DEFAULT_TASK.extract_generated_code(response, language)


def _parse_review_response(response: str) -> dict:
    return DEFAULT_TASK.parse_review_response(response)


def route_review(state: GraphState) -> str:
    """
    Routing logic after review node.
    Decides whether to continue generating or end.
    """
    review = state.get('review', {})
    approved = review.get('approved', False)
    iteration = state.get('iteration', 0)
    max_iterations = state.get('max_iterations', 3)
    
    logger.debug(
        f"Routing decision: approved={approved}, iteration={iteration}/{max_iterations}"
    )
    
    # If approved, we're done
    if approved:
        # Update stop reason in state (for END nodes, state mods don't persist, but set anyway)
        state['stop_reason'] = 'approved_by_reviewer'
        logger.info("Code approved, ending workflow")
        return END
    
    # If max iterations reached, stop
    if iteration >= max_iterations:
        state['stop_reason'] = 'max_iterations_reached'
        logger.info(f"Max iterations ({max_iterations}) reached, ending workflow")
        return END
    
    # Otherwise, generate again
    logger.info(f"Code not approved (iteration {iteration}/{max_iterations}), routing back to generate")
    return 'generate'


def route_verify(state: GraphState) -> str:
    verification = state.get("verification") or {}

    if verification.get("passed", False):
        return "review"

    return END


def create_graph(task: RuntimeTask | None = None):
    """Creates the LangGraph workflow for the selected runtime task."""
    active_task = task or DEFAULT_TASK

    async def fetch_context_node(state: GraphState) -> GraphState:
        return await _fetch_context(state, active_task)

    async def generate_node(state: GraphState) -> GraphState:
        return await _generate(state, active_task)

    async def verify_node(state: GraphState) -> GraphState:
        return await _verify(state, active_task)

    async def review_node(state: GraphState) -> GraphState:
        return await _review(state, active_task)

    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node('fetch_context', fetch_context_node)
    workflow.add_node('generate', generate_node)
    workflow.add_node('verify', verify_node)
    workflow.add_node('review', review_node)
    
    # Set up edges
    workflow.set_entry_point('fetch_context')
    workflow.add_edge('fetch_context', 'generate')
    workflow.add_edge('generate', 'verify')
    workflow.add_conditional_edges(
        'verify',
        route_verify,
        {
            'review': 'review',
            END: END,
        }
    )
    workflow.add_conditional_edges(
        'review',
        route_review,
        {
            'generate': 'generate',
            END: END,
        }
    )
    
    return workflow.compile()

