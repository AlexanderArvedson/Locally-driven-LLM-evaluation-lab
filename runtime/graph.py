from __future__ import annotations
from langgraph.graph import StateGraph, END
from .state import GraphState

def create_graph():
    """Creates the LangGraph workflow."""
    workflow = StateGraph(GraphState)

    # Define nodes
    def fetch_context(state: GraphState) -> GraphState:
        print("---FETCHING CONTEXT---")
        state['iteration'] += 1
        state['context'] = "some_context" # Placeholder
        return state

    def generate(state: GraphState) -> GraphState:
        print("---GENERATING CODE---")
        state['generation'] = "generated_code" # Placeholder
        return state

    def review(state: GraphState) -> GraphState:
        print("---REVIEWING CODE---")
        # Simulate a review process
        if "fail" in state.get('initial_prompt', ''):
             state['review'] = "failed"
        else:
             state['review'] = "passed"
        return state

    def validate(state: GraphState) -> GraphState:
        print("---VALIDATING CODE---")
        state['validation_result'] = "passed" # Placeholder
        return state

    # Define edges
    def should_continue(state: GraphState):
        if state['iteration'] >= state['max_iterations']:
            state['stop_reason'] = "max_iterations_reached"
            return "end"
        if state.get('review') == "passed":
            return "validate"
        else:
            return "generate"

    workflow.add_node("fetch_context", fetch_context)
    workflow.add_node("generate", generate)
    workflow.add_node("review", review)
    workflow.add_node("validate", validate)

    workflow.set_entry_point("fetch_context")
    workflow.add_edge("fetch_context", "generate")
    workflow.add_edge("generate", "review")
    workflow.add_conditional_edges(
        "review",
        should_continue,
        {
            "validate": "validate",
            "generate": "generate",
            "end": END
        }
    )
    workflow.add_edge("validate", END)

    return workflow.compile()
