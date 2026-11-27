"""Where an agent thread's gauge reaches 100%."""

import pytest

from modules.agent.context_use.agent_usage import agent_budget
from modules.agent.opencode_config import compaction_point

pytestmark = pytest.mark.unit


def test_a_server_that_reports_a_smaller_window_than_opencode_assumes_sets_the_limit() -> None:
    """opencode is told 32,768, but the server refuses a request past its own
    16,384, long before opencode would summarise."""
    assert agent_budget(configured=32_768, reported=16_384) == 16_384


def test_with_no_report_it_is_where_opencode_summarises() -> None:
    assert agent_budget(configured=32_768, reported=None) == compaction_point(32_768)


def test_a_server_that_reports_the_window_opencode_has_leaves_the_compaction_point() -> None:
    """opencode summarises before the window is full, so that comes first."""
    assert agent_budget(configured=16_384, reported=16_384) == compaction_point(16_384)


def test_a_server_that_reports_a_larger_window_leaves_the_compaction_point() -> None:
    assert agent_budget(configured=32_768, reported=100_000) == compaction_point(32_768)
