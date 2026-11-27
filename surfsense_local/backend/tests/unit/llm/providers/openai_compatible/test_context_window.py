"""An endpoint that is a llama-server tells how big its window is."""

import httpx
import pytest

from modules.llm.providers.openai_compatible.chat import OpenAICompatibleChatProvider

pytestmark = pytest.mark.unit

LAN = "http://100.73.187.110:8080/v1"


def provider(
    answer: httpx.Response | Exception,
    seen: list[httpx.Request] | None = None,
    base_url: str = LAN,
    api_key: str | None = "secret-key",
) -> OpenAICompatibleChatProvider:
    def handle(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        if isinstance(answer, Exception):
            raise answer
        return answer

    return OpenAICompatibleChatProvider(
        base_url, api_key, transport=httpx.MockTransport(handle)
    )


def props(n_ctx: object) -> httpx.Response:
    return httpx.Response(200, json={"default_generation_settings": {"n_ctx": n_ctx}})


async def test_the_window_is_what_the_server_reports() -> None:
    assert await provider(props(32768)).context_tokens("qwen") == 32768


async def test_it_asks_props_with_the_connections_key() -> None:
    seen: list[httpx.Request] = []

    await provider(props(8192), seen).context_tokens("qwen")

    assert [str(request.url) for request in seen] == [
        "http://100.73.187.110:8080/props"
    ]
    assert seen[0].headers["Authorization"] == "Bearer secret-key"


@pytest.mark.parametrize(
    "answer",
    [
        httpx.Response(401, json={"error": {"message": "Invalid API Key"}}),
        httpx.Response(404, text="not found"),
        httpx.Response(200, text="<html>not json</html>"),
        httpx.Response(200, json={"object": "list", "data": []}),
        httpx.Response(200, json={"default_generation_settings": {}}),
        props(None),
        props(0),
        props("32768"),
        props(True),
        httpx.ConnectError("unreachable"),
        httpx.ReadTimeout("slow"),
    ],
    ids=[
        "refused key",
        "no such route",
        "not json",
        "the models listing instead",
        "no window in it",
        "null window",
        "zero window",
        "window as text",
        "window as a boolean",
        "unreachable",
        "timed out",
    ],
)
async def test_anything_short_of_a_clean_window_is_unknown(
    answer: httpx.Response | Exception,
) -> None:
    assert await provider(answer).context_tokens("qwen") is None


async def test_a_service_on_the_internet_is_not_asked_at_all() -> None:
    seen: list[httpx.Request] = []

    window = await provider(
        props(128000), seen, base_url="https://api.openai.com/v1"
    ).context_tokens("gpt")

    assert window is None
    assert seen == []
