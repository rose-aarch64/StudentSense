def context_usage_frame(used: int, budget: int | None) -> dict:
    """How much of the history budget a thread has spent; no budget for an agent thread."""
    return {"type": "context-usage", "used": used, "budget": budget}
