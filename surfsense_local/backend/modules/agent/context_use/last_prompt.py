from collections import OrderedDict

# Sessions kept; the least recently heard from make room. A restart forgets all
# of them, and the gauge waits for the session's next step.
LIMIT = 512

_sizes: OrderedDict[str, int] = OrderedDict()


def note_prompt(session_id: str, tokens: int) -> None:
    """The size of the prompt a session's latest step sent the model."""
    _sizes[session_id] = tokens
    _sizes.move_to_end(session_id)
    while len(_sizes) > LIMIT:
        _sizes.popitem(last=False)


def last_prompt(session_id: str | None) -> int | None:
    """What the session's latest step sent, or None before it has sent one."""
    return None if session_id is None else _sizes.get(session_id)


def forget_all() -> None:
    _sizes.clear()
