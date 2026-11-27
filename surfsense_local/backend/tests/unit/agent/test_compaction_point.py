"""Where opencode starts summarising a session: what 100% of the agent's gauge is."""

import json
from pathlib import Path

import pytest

from modules.agent.opencode_config import (
    AgentSetup,
    compaction_point,
    opencode_config,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("window", "point"),
    [
        # The answer room is a quarter of a small window, which the reserve floor passes.
        (16_384, 12_288),
        (32_768, 24_576),
        # A larger window reserves a tenth of it, up to the 32,000 an answer is capped at.
        (200_000, 180_000),
        (1_000_000, 968_000),
    ],
)
def test_the_point_is_the_window_less_the_room_compaction_keeps(
    window: int, point: int
) -> None:
    assert compaction_point(window) == point


@pytest.mark.parametrize("window", [16_384, 32_768, 200_000])
def test_it_agrees_with_the_buffer_written_to_opencodes_configuration(
    window: int, tmp_path: Path
) -> None:
    setup = AgentSetup(
        model="m",
        window=window,
        reads_images=False,
        endpoint_url="http://127.0.0.1:8123/agent/model/v1",
        launch_key="k",
        route="chat_completions",
    )

    written = json.loads(json.dumps(opencode_config(setup, tmp_path)))

    assert window - written["compaction"]["buffer"] == compaction_point(window)
