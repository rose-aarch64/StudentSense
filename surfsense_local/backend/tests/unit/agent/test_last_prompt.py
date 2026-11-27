"""The prompt size each agent session last sent a model, kept while the app runs."""

import pytest

from modules.agent.context_use import last_prompt as store

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def empty() -> None:
    store.forget_all()


def test_the_latest_size_for_a_session_is_kept() -> None:
    store.note_prompt("ses_a", 1000)
    store.note_prompt("ses_a", 1800)

    assert store.last_prompt("ses_a") == 1800


def test_sessions_are_kept_apart() -> None:
    store.note_prompt("ses_a", 1000)
    store.note_prompt("ses_b", 2000)

    assert (store.last_prompt("ses_a"), store.last_prompt("ses_b")) == (1000, 2000)


def test_a_session_never_heard_from_has_none() -> None:
    assert store.last_prompt("ses_new") is None
    assert store.last_prompt(None) is None


def test_the_oldest_sessions_make_room_past_the_limit() -> None:
    for number in range(store.LIMIT + 1):
        store.note_prompt(f"ses_{number}", 10)

    assert store.last_prompt("ses_0") is None
    assert store.last_prompt(f"ses_{store.LIMIT}") == 10


def test_a_session_heard_from_again_is_not_the_oldest() -> None:
    for number in range(store.LIMIT):
        store.note_prompt(f"ses_{number}", 10)
    store.note_prompt("ses_0", 20)
    store.note_prompt("ses_new", 10)

    assert store.last_prompt("ses_0") == 20
    assert store.last_prompt("ses_1") is None
