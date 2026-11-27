"""Where a connection's own server may be asked how big its window is."""

import pytest

from modules.llm.connections.props_url import props_url

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("base_url", "expected"),
    [
        ("http://100.73.187.110:8080/v1", "http://100.73.187.110:8080/props"),
        ("http://100.73.187.110:8080/v1/", "http://100.73.187.110:8080/props"),
        ("http://100.73.187.110:8080", "http://100.73.187.110:8080/props"),
        ("http://127.0.0.1:8080/v1", "http://127.0.0.1:8080/props"),
        ("http://localhost:8080/v1", "http://localhost:8080/props"),
        ("http://192.168.1.20:8080/v1", "http://192.168.1.20:8080/props"),
        ("http://10.0.0.5/v1", "http://10.0.0.5/props"),
        ("http://box.local:8080/v1", "http://box.local:8080/props"),
        ("http://sbox.tailbe4fdf.ts.net:8080/v1", "http://sbox.tailbe4fdf.ts.net:8080/props"),
    ],
)
def test_a_server_on_this_machine_or_network_can_be_asked(
    base_url: str, expected: str
) -> None:
    assert props_url(base_url) == expected


@pytest.mark.parametrize(
    "base_url",
    [
        "https://api.openai.com/v1",
        "https://api.anthropic.com/v1",
        "https://openrouter.ai/api/v1",
        "http://8.8.8.8/v1",
        "https://llama.example.com/v1",
        "not a url",
    ],
)
def test_a_service_on_the_internet_is_never_asked(base_url: str) -> None:
    """Its key would ride an extra request to a route it does not have."""
    assert props_url(base_url) is None
