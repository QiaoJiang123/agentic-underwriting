from typing import Any, Callable, TypedDict


class UnderwritingState(TypedDict, total=False):
    messages: list[dict[str, str]]
    model: str
    api_key: str
    guide_instructions: list[str]
    underwriter_notes: list[str]
    reply: str
    response_id: str | None


def run_underwriting_graph(
    messages: list[dict[str, str]],
    model: str,
    api_key: str,
    guide_instructions: list[str],
    underwriter_notes: list[str],
    call_openai: Callable[..., dict[str, Any]],
):
    try:
        return run_langgraph(
            messages,
            model,
            api_key,
            guide_instructions,
            underwriter_notes,
            call_openai,
        )
    except ModuleNotFoundError:
        return call_underwriting_model(
            {
                "messages": messages,
                "model": model,
                "api_key": api_key,
                "guide_instructions": guide_instructions,
                "underwriter_notes": underwriter_notes,
            },
            call_openai,
        )


def run_langgraph(messages, model, api_key, guide_instructions, underwriter_notes, call_openai):
    from langgraph.graph import END, START, StateGraph

    def underwriting_model_node(state: UnderwritingState):
        return call_underwriting_model(state, call_openai)

    graph = StateGraph(UnderwritingState)
    graph.add_node("underwriting_model", underwriting_model_node)
    graph.add_edge(START, "underwriting_model")
    graph.add_edge("underwriting_model", END)
    compiled = graph.compile()

    return compiled.invoke(
        {
            "messages": messages,
            "model": model,
            "api_key": api_key,
            "guide_instructions": guide_instructions,
            "underwriter_notes": underwriter_notes,
        }
    )


def call_underwriting_model(state, call_openai):
    response = call_openai(
        api_key=state["api_key"],
        model=state["model"],
        messages=state["messages"],
        guide_instructions=state.get("guide_instructions", []),
        underwriter_notes=state.get("underwriter_notes", []),
    )
    return {
        **state,
        "reply": response.get("reply", ""),
        "response_id": response.get("id"),
    }
