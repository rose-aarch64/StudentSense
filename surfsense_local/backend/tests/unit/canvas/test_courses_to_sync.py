from datetime import UTC, datetime

from modules.canvas.sync.term import courses_to_sync

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)

FALL = {
    "name": "2026/FA",
    "start_at": "2026-08-19T04:00:00Z",
    "end_at": "2026-12-19T05:00:00Z",
}
LAST_FALL = {
    "name": "2025/FA",
    "start_at": "2025-08-19T04:00:00Z",
    "end_at": "2025-12-19T05:00:00Z",
}
DEFAULT = {"name": "Default Term", "start_at": None, "end_at": None}


def course(course_id: int, name: str, term: dict | None) -> dict:
    """A course as Canvas lists it, with its term."""
    return {"id": course_id, "name": name, "term": term}


def ids(courses: list[dict]) -> list[int]:
    """The ids that were kept, in the order Canvas listed them."""
    return [c["id"] for c in courses]


def test_only_courses_in_a_term_that_covers_today_are_synced() -> None:
    """The orientation course sits in a term with no dates, and is left out."""
    courses = [
        course(1, "Networks", FALL),
        course(2, "Welcome to BC", DEFAULT),
        course(3, "Old class", LAST_FALL),
    ]

    assert ids(courses_to_sync(courses, None, NOW)) == [1]


def test_a_term_with_only_a_start_is_current_once_it_has_begun() -> None:
    """Canvas terms often leave the end open."""
    open_ended = {"name": "2026/FA", "start_at": "2026-08-19T04:00:00Z"}
    courses = [course(1, "A", open_ended), course(2, "B", DEFAULT)]

    assert ids(courses_to_sync(courses, None, NOW)) == [1]


def test_a_school_with_no_dated_terms_syncs_everything() -> None:
    """Without dates there is no way to say which term is current."""
    courses = [course(1, "A", DEFAULT), course(2, "B", None)]

    assert ids(courses_to_sync(courses, None, NOW)) == [1, 2]


def test_between_terms_nothing_is_synced() -> None:
    """Old classes do not come back just because the new term has not begun."""
    later = datetime(2027, 1, 5, tzinfo=UTC)
    courses = [course(1, "A", FALL), course(2, "B", DEFAULT)]

    assert courses_to_sync(courses, None, later) == []


def test_a_named_term_is_taken_exactly() -> None:
    """Asking for a term by name overrides the dates, as it always did."""
    courses = [course(1, "A", FALL), course(2, "B", LAST_FALL)]

    assert ids(courses_to_sync(courses, "2025/FA", NOW)) == [2]
