import json


def prompt_tokens_of(line: str) -> int | None:
    """The prompt size on a stream line that reports usage, else None.

    Only a model that was asked for usage sends it, on the last chunk.
    """
    # Checked before parsing, since this reads every line of every stream.
    if not line.startswith("data:") or '"prompt_tokens"' not in line:
        return None
    try:
        usage = json.loads(line[len("data:") :]).get("usage")
        tokens = usage.get("prompt_tokens")
    except (ValueError, AttributeError):
        return None
    if isinstance(tokens, int) and not isinstance(tokens, bool) and tokens > 0:
        return tokens
    return None
