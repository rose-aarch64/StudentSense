from modules.canvas.sync.linked_files import linked_file_ids

SCHOOL = "school.edu"


def ids(*texts: str, course_id: int = 1) -> list[int]:
    """The file ids a class's texts link to, for course 1 on school.edu."""
    return linked_file_ids(texts, course_id, SCHOOL)


def test_a_relative_and_an_absolute_link_both_name_their_file() -> None:
    """Canvas writes links both ways, and a student sees no difference."""
    text = (
        "[a](/courses/1/files/10) [b](https://school.edu/courses/1/files/11) "
        '<a href="/courses/1/files/12">c</a>'
    )

    assert ids(text) == [10, 11, 12]


def test_a_query_or_a_preview_or_a_download_suffix_still_names_the_file() -> None:
    """The same file is linked as a page, a thumbnail and a download."""
    text = (
        "[a](/courses/1/files/10?wrap=1) [b](/courses/1/files/11/preview?verifier=x) "
        "[c](/courses/1/files/12/download?download_frd=1)"
    )

    assert ids(text) == [10, 11, 12]


def test_a_file_linked_twice_is_named_once_in_the_order_first_seen() -> None:
    """One file, one download."""
    assert ids(
        "[a](/courses/1/files/5) [b](/courses/1/files/4)", "[c](/courses/1/files/5)"
    ) == [5, 4]


def test_another_courses_file_is_ignored() -> None:
    """The token reads this course; another course's file is not its to fetch."""
    assert ids("[a](/courses/9/files/5)") == []


def test_a_link_on_another_host_is_ignored() -> None:
    """Only the school's own Canvas is asked, and only with the school's token."""
    assert ids("[a](https://other.example/courses/1/files/5)") == []


def test_a_path_inside_another_hosts_address_is_ignored() -> None:
    """A mirror or a protocol-relative address is not the school's course path."""
    assert ids("[a](//evil.com/courses/1/files/5)") == []
    assert ids("[b](https://evil.com/mirror/courses/1/files/6)") == []
    assert ids("[c](/mirror/courses/1/files/7)") == []


def test_a_path_after_a_quote_or_a_bracket_still_names_its_file() -> None:
    """The boundary check must not lose a link written in HTML or markdown."""
    assert ids('<a href="/courses/1/files/8">x</a> [y](/courses/1/files/9)') == [8, 9]


def test_a_link_that_is_not_a_file_is_ignored() -> None:
    """A page or an assignment is not a download."""
    assert ids("[a](/courses/1/pages/intro) [b](/courses/1/assignments/3)") == []
