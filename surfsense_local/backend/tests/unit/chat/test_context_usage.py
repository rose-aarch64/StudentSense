"""The frame that tells a window how full a thread's history is."""

import pytest

from modules.chat.context_usage import context_usage_frame

pytestmark = pytest.mark.unit


def test_the_frame_carries_used_and_budget() -> None:
    assert context_usage_frame(120, 3000) == {
        "type": "context-usage",
        "used": 120,
        "budget": 3000,
    }


def test_the_frame_carries_a_null_budget_when_there_is_none() -> None:
    assert context_usage_frame(120, None)["budget"] is None
