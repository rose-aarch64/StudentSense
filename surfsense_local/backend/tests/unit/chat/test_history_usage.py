"""How much of the history budget a thread's history has spent."""

import pytest

from modules.chat.budget import IMAGE_TOKENS
from modules.chat.history import build_messages
from modules.chat.history_usage import history_usage
from modules.chat.models import ChatMessage, MessageRole

pytestmark = pytest.mark.unit


def _turn(marker: str, tokens: int, id: int | None = None) -> ChatMessage:
    # Four characters per estimated token, matching the trimmer's heuristic.
    return ChatMessage(
        id=id, role=MessageRole.USER, content={"text": marker * (tokens * 4)}
    )


def _message(role: MessageRole, text: str, ending: dict | None = None) -> ChatMessage:
    content: dict = {"text": text}
    if ending is not None:
        content["ending"] = ending
    return ChatMessage(role=role, content=content)


async def test_usage_sums_every_turn_from_the_start() -> None:
    assert await history_usage([_turn("a", 10), _turn("b", 10), _turn("c", 10)]) == 30


async def test_usage_is_not_capped_by_any_budget() -> None:
    assert await history_usage([_turn("a", 2500), _turn("b", 2500)]) == 5000


async def test_usage_begins_at_the_history_start_id() -> None:
    history = [_turn("a", 10, id=1), _turn("b", 10, id=2), _turn("c", 10, id=3)]

    assert await history_usage(history, history_start_id=2) == 20


async def test_usage_leaves_out_a_failed_turn_and_its_question() -> None:
    history = [
        _message(MessageRole.USER, "x" * 40),
        _message(
            MessageRole.ASSISTANT,
            "",
            {"type": "error", "kind": "network", "message": "unreachable"},
        ),
        _message(MessageRole.USER, "y" * 40),
        _message(MessageRole.ASSISTANT, "z" * 40),
    ]

    assert await history_usage(history) == 20


async def test_usage_prefers_an_exact_counter() -> None:
    async def exact(text: str) -> int:
        return 40

    assert await history_usage([_turn("q", 1)], token_count=exact) == 40


async def test_usage_falls_back_to_the_heuristic_when_the_counter_fails() -> None:
    async def unavailable(text: str) -> int | None:
        return None

    assert await history_usage([_turn("q", 7)], token_count=unavailable) == 7


async def test_usage_prices_only_the_newest_picture_turn() -> None:
    picture = {"text": "", "images": [{"mime": "image/png", "path": "p"}]}
    history = [
        ChatMessage(role=MessageRole.USER, content=picture),
        ChatMessage(role=MessageRole.USER, content=picture),
    ]

    assert await history_usage(history) == IMAGE_TOKENS


async def test_usage_leaves_out_the_older_picture_when_this_turn_brings_its_own() -> None:
    """The trim resends one earlier picture only to a turn with none of its own."""
    picture = {"text": "", "images": [{"mime": "image/png", "path": "p"}]}
    history = [ChatMessage(role=MessageRole.USER, content=picture)]

    assert await history_usage(history, resend_picture=False) == 0


async def test_usage_of_nothing_is_zero() -> None:
    assert await history_usage([]) == 0


async def test_usage_matches_what_the_trim_keeps_when_nothing_is_cut() -> None:
    history = [_turn("a", 30), _turn("b", 40)]

    kept = (await build_messages("S", history, "ask", history_budget=1000)).messages[
        1:-1
    ]

    assert len(kept) == 2
    assert await history_usage(history) == 70
