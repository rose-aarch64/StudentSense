import re
from collections.abc import Iterable

# A Canvas file's page, preview or download, as an absolute or a relative address.
# The lookbehind keeps a path that sits inside another host's address, or after
# another path, from being read as the school's own.
_FILE_LINK = re.compile(
    r"(?<![A-Za-z0-9.\-])(?:https?://([^/\s\"'<>()]+))?/courses/(\d+)/files/(\d+)"
)


def linked_file_ids(
    texts: Iterable[str], course_id: int, school_host: str
) -> list[int]:
    """The files of this course that the texts link to, each once, in the order
    first seen. A link to another course, or to another host, is not the token's
    to follow."""
    seen: dict[int, None] = {}
    for text in texts:
        for host, course, file_id in _FILE_LINK.findall(text):
            if int(course) != course_id:
                continue
            if host and host.lower() != school_host.lower():
                continue
            seen.setdefault(int(file_id))
    return list(seen)
