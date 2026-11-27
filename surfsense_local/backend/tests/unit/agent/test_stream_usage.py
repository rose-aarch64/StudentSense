"""The prompt size a model reports on the last line of a stream."""

import json

import pytest

from modules.agent.model_endpoint.stream_usage import prompt_tokens_of

pytestmark = pytest.mark.unit


def line(payload: object) -> str:
    return f"data: {json.dumps(payload)}"


def test_the_prompt_size_is_read_from_the_usage_chunk() -> None:
    chunk = {
        "choices": [],
        "usage": {"prompt_tokens": 5120, "completion_tokens": 40, "total_tokens": 5160},
    }

    assert prompt_tokens_of(line(chunk)) == 5120


@pytest.mark.parametrize(
    "text",
    [
        line({"choices": [{"delta": {"content": "Hello"}}]}),
        line({"choices": [{"delta": {}}], "usage": None}),
        line({"usage": {"completion_tokens": 3}}),
        line({"usage": {"prompt_tokens": "5120"}}),
        line({"usage": {"prompt_tokens": 0}}),
        line({"usage": {"prompt_tokens": True}}),
        line({"usage": {"prompt_tokens": -5}}),
        line([1, 2]),
        'data: {"usage": {"prompt_tokens": 12',
        "data: [DONE]",
        ": keep-alive",
        "",
    ],
    ids=[
        "an ordinary delta",
        "usage null",
        "no prompt size",
        "prompt size as text",
        "zero",
        "boolean",
        "negative",
        "not an object",
        "cut off json",
        "done",
        "comment",
        "blank",
    ],
)
def test_any_other_line_has_no_prompt_size(text: str) -> None:
    assert prompt_tokens_of(text) is None
