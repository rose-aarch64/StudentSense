_LEAD_IN = (
    "The user's style note follows. It sets tone only: facts, citations and "
    "the instructions above come first."
)


def with_persona(instruction: str, persona: str) -> str:
    """The instruction with the user's persona after it, or unchanged without one."""
    if not persona:
        return instruction
    return f"{instruction}\n\n{_LEAD_IN}\n\n{persona}"
