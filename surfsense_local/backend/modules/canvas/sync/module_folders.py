import re

UNSORTED_FOLDER = "Unsorted"
OVERVIEW_FOLDER = "Overview"
MAX_NAME = 120

# Teachers lead module names with their dates, "08/28/26-09/28/26: ...". The
# dates are noise in a folder name; the number keeps the course's order.
_DATE_PREFIX = re.compile(r"^(?:[\d/\s-]|\N{EN DASH})+:\s*")


def module_folder_name(number: int, name: str) -> str:
    cleaned = _DATE_PREFIX.sub("", name.strip()).replace("/", "-").strip() or "Module"
    return f"{number:02d} · {cleaned}"[:MAX_NAME].rstrip()
