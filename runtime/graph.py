from __future__ import annotations

import logging
from langgraph.graph import StateGraph, END
from .state import GraphState
from .llm import call_ollama
from .prompts import generate_refactoring_prompt, generate_review_prompt

logger = logging.getLogger(__name__)


async def fetch_context(state: GraphState) -> GraphState:
    """
    Fetch and normalize context for the refactoring task.
    Extracts context from job input and prepares it for the workflow.
    """
    logger.info("---FETCHING CONTEXT---")
    
    # Context is already in state, just normalize it
    context = state.get('optional_context')
    state['context'] = context if context else ""
    
    return state


async def generate(state: GraphState) -> GraphState:
    """
    Generate refactored code using the LLM.
    """
    logger.info("---GENERATING CODE---")
    
    try:
        # Build the refactoring prompt
        prompt = generate_refactoring_prompt(
            code=state['code_to_refactor'],
            language=state['language'],
            context=state.get('context'),
        )
        
        logger.debug(f"Calling LLM for generation (iteration {state['iteration']})")
        
        # Call Ollama
        response = await call_ollama(prompt)
        
        # Parse the response to extract code
        generated_code = _extract_code_from_response(response, state['language'])
        
        state['generation'] = generated_code
        logger.debug(f"Generated code: {len(generated_code)} chars")
        
    except Exception as e:
        logger.error(f"Error during code generation: {str(e)}")
        state['generation'] = None
        state['stop_reason'] = f"generation_error: {str(e)}"
    
    return state


async def review(state: GraphState) -> GraphState:
    """
    Review the generated code and provide feedback.
    Returns a structured review with approval status.
    """
    logger.info("---REVIEWING CODE---")
    
    # Increment iteration counter
    state['iteration'] = state.get('iteration', 0) + 1
    
    if state.get('generation') is None:
        logger.warning("No generated code to review")
        state['review'] = {
            'approved': False,
            'feedback': 'No code was generated',
            'score': 0.0,
        }
        return state
    
    try:
        # Build the review prompt
        prompt = generate_review_prompt(
            original_code=state['code_to_refactor'],
            generated_code=state['generation'],
            language=state['language'],
            context=state.get('context'),
        )
        
        logger.debug("Calling LLM for review")
        
        # Call Ollama
        response = await call_ollama(prompt)
        
        # Parse the review response
        review_data = _parse_review_response(response)
        
        state['review'] = review_data
        logger.debug(f"Review score: {review_data.get('score', 'N/A')}")
        
    except Exception as e:
        logger.error(f"Error during code review: {str(e)}")
        state['review'] = {
            'approved': False,
            'feedback': f'Review failed: {str(e)}',
            'score': 0.0,
        }
    
    return state


def _extract_code_from_response(response: str, language: str) -> str:
    """
    Extract code from the LLM response.
    Looks for code blocks marked with triple backticks.
    """
    # Try to extract code from markdown code blocks
    import re
    
    # Pattern for code blocks with language specified
    pattern = rf'```{re.escape(language)}\n(.*?)\n```'
    match = re.search(pattern, response, re.DOTALL)
    if match:
        return match.group(1)
    
    # Pattern for generic code blocks
    pattern = r'```\n(.*?)\n```'
    match = re.search(pattern, response, re.DOTALL)
    if match:
        return match.group(1)
    
    # If no code block found, return the entire response as-is
    # (LLM might have provided code without markdown)
    return response.strip()


def _parse_review_response(response: str) -> dict:
    """
    Parse the review response from the LLM.
    Extracts approval status, feedback, and score.
    """
    import re
    
    review_data = {
        'approved': False,
        'feedback': response,
        'score': 0.0,
    }
    
    # Look for yes/no answers
    if re.search(r'\byes\b', response, re.IGNORECASE):
        review_data['approved'] = True
    elif re.search(r'\bno\b', response, re.IGNORECASE):
        review_data['approved'] = False
    
    # Try to extract a score (1-10)
    score_match = re.search(r'(\d+)\s*(?:/10|out of 10)', response, re.IGNORECASE)
    if score_match:
        try:
            score = int(score_match.group(1))
            review_data['score'] = min(10, max(0, score))  # Clamp to 0-10
        except ValueError:
            pass
    
    return review_data


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


def create_graph():
    """Creates the LangGraph workflow for code refactoring."""
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node('fetch_context', fetch_context)
    workflow.add_node('generate', generate)
    workflow.add_node('review', review)
    
    # Set up edges
    workflow.set_entry_point('fetch_context')
    workflow.add_edge('fetch_context', 'generate')
    workflow.add_edge('generate', 'review')
    workflow.add_conditional_edges(
        'review',
        route_review,
        {
            'generate': 'generate',
            END: END,
        }
    )
    
    return workflow.compile()

