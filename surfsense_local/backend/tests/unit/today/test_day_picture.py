from datetime import UTC, datetime, timedelta, timezone

from modules.today.picture import OpenTask, day_picture

EST = timezone(timedelta(hours=-5))
# Tuesday 24 Nov 2026, 9:30 in the morning for the user.
NOW = datetime(2026, 11, 24, 9, 30, tzinfo=EST)


def due(year: int, month: int, day: int, hour: int = 23, minute: int = 59):
    """A due time as Canvas stores it: UTC, with no zone attached."""
    local = datetime(year, month, day, hour, minute, tzinfo=EST)
    return local.astimezone(UTC).replace(tzinfo=None)


def test_it_states_the_date_the_user_is_living_in() -> None:
    """The model cannot plan a day it does not know the date of."""
    picture = day_picture([], NOW)

    assert "Tuesday, November 24, 2026" in picture
    assert "No open tasks" in picture


def test_a_task_due_tonight_is_due_today_in_eastern() -> None:
    """11:59 PM there is already the 25th in UTC; it must still read as today."""
    task = OpenTask(1, "Lab report", due(2026, 11, 24), "Photography")

    picture = day_picture([task], NOW)

    assert "[Photography] Lab report" in picture.split("Due today:")[1]


def test_tasks_fall_into_the_sections_the_to_do_list_shows() -> None:
    """The model schedules from these groups, so each task is in exactly one."""
    tasks = [
        OpenTask(1, "Missed quiz", due(2026, 11, 20), "Network Security"),
        OpenTask(2, "Thursday lab", due(2026, 11, 26), None),
        OpenTask(3, "Essay draft", due(2026, 11, 30), "War/Peace/Pacific"),
        OpenTask(4, "Read ahead", None, None),
    ]

    picture = day_picture(tasks, NOW)

    assert "Missed quiz" in picture.split("Overdue:")[1].split("Later")[0]
    assert "Thursday lab" in picture.split("Later this week:")[1].split("Next")[0]
    assert "Essay draft" in picture.split("Next week:")[1].split("No due")[0]
    assert "Read ahead" in picture.split("No due date:")[1]
    assert picture.count("Essay draft") == 1


def test_tasks_from_long_ago_and_far_ahead_are_left_out() -> None:
    """A 2024 orientation task is not today's business, nor is next semester's."""
    tasks = [
        OpenTask(1, "Orientation", due(2024, 8, 22), "Welcome"),
        OpenTask(2, "Final project", due(2027, 3, 1), "Photography"),
    ]

    picture = day_picture(tasks, NOW)

    assert "Orientation" not in picture
    assert "Final project" not in picture
