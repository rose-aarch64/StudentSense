from collections.abc import Sequence

from modules.chat.budget import IMAGE_TOKENS
from modules.chat.history import (
    TokenCounter,
    _answered,
    _cost,
    _newest_image_turn,
    message_text,
)
from modules.chat.models import ChatMessage


async def history_usage(
    history: Sequence[ChatMessage],
    *,
    history_start_id: int | None = None,
    token_count: TokenCounter | None = None,
    resend_picture: bool = True,
) -> int:
    """Tokens the history spends from `history_start_id` on, before any trim.

    Prices turns as the trim does, so 100% of the budget is where it starts
    cutting. Image references are counted without loading the files. The
    newest earlier picture rides along only to a turn with none of its own,
    so `resend_picture` is False for a turn that attaches pictures.
    """
    answered = _answered(history)
    newest_picture = _newest_image_turn(answered) if resend_picture else None
    total = 0
    for row in answered:
        if history_start_id is not None and row.id is not None:
            if row.id < history_start_id:
                continue
        total += await _cost(message_text(row), token_count)
        if row is newest_picture:
            total += IMAGE_TOKENS * len(row.content["images"])
    return total
