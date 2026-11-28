def assignment_refs(assignments: list[dict]) -> dict[tuple[str, int], int]:
    """(module item type, its content id) -> the assignment it stands for.

    Canvas lists a graded quiz or discussion among a course's assignments, but a
    module names it by the quiz's or the topic's own id.
    """
    refs: dict[tuple[str, int], int] = {}
    for assignment in assignments:
        refs[("Assignment", assignment["id"])] = assignment["id"]
        quiz_id = assignment.get("quiz_id")
        if quiz_id is not None:
            refs[("Quiz", quiz_id)] = assignment["id"]
        topic_id = (assignment.get("discussion_topic") or {}).get("id")
        if topic_id is not None:
            refs[("Discussion", topic_id)] = assignment["id"]
    return refs


def assignment_id_of(item: dict, refs: dict[tuple[str, int], int]) -> int | None:
    """The assignment a module item stands for, or None when it is not one."""
    return refs.get((item.get("type"), item.get("content_id")))
