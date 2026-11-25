from datetime import datetime


def _moment(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _dates(course: dict) -> tuple[datetime | None, datetime | None]:
    term = course.get("term") or {}
    return _moment(term.get("start_at")), _moment(term.get("end_at"))


def courses_to_sync(courses: list[dict], term: str | None, now: datetime) -> list[dict]:
    """The courses a sync brings in: those of the term named, else of the current one.

    A term is current when `now` falls between its dates; an open end counts as
    not yet over. A course in a term with no dates, such as an orientation course
    in Canvas's "Default Term", is left out. A school whose terms have no dates
    at all gets every course, since nothing could say which is current. Between
    terms nothing is synced: last term's classes do not return.
    """
    if term is not None:
        return [c for c in courses if (c.get("term") or {}).get("name") == term]
    dated = [c for c in courses if any(_dates(c))]
    if not dated:
        return courses
    return [
        c
        for c in dated
        if (_dates(c)[0] is None or _dates(c)[0] <= now)
        and (_dates(c)[1] is None or now <= _dates(c)[1])
    ]
