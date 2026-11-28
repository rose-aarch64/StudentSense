from modules.canvas.html_text import html_to_text


def test_a_link_keeps_its_address_as_a_markdown_link() -> None:
    """A model and the reader both need where the words point."""
    html = '<p>See <a href="https://example.org/x">the guide</a> now</p>'

    assert html_to_text(html) == "See [the guide](https://example.org/x) now"


def test_a_link_whose_text_is_its_address_shows_the_address_once() -> None:
    """Repeating an address as its own link text would only be noise."""
    html = '<p><a href="https://example.org/x">https://example.org/x</a></p>'

    assert html_to_text(html) == "https://example.org/x"


def test_a_link_around_markup_keeps_the_words() -> None:
    """Bold or italic inside a link is still the link's text."""
    html = '<a href="https://example.org/x"><strong>Guide</strong></a>'

    assert html_to_text(html) == "[Guide](https://example.org/x)"


def test_a_link_with_no_words_shows_its_address() -> None:
    """An empty anchor has no words to carry the link, so its address stands alone."""
    html = '<a href="https://example.org/x"></a>'

    assert html_to_text(html) == "https://example.org/x"


def test_an_image_keeps_its_description_and_address_as_a_markdown_image() -> None:
    """The picture is part of the lab's instructions; its address must survive."""
    html = '<p><img src="https://example.org/a.png" alt="A chart"></p>'

    assert html_to_text(html) == "![A chart](https://example.org/a.png)"


def test_a_linked_image_keeps_both_the_picture_and_the_link() -> None:
    """A picture that is also a link is common in a lab's instructions."""
    html = '<a href="https://example.org/x"><img src="/a.png" alt="chart"></a>'

    assert html_to_text(html) == "[![chart](/a.png)](https://example.org/x)"


def test_an_image_with_no_description_keeps_only_its_address() -> None:
    """The address is all there is to keep."""
    html = '<img src="https://example.org/a.png">'

    assert html_to_text(html) == "![](https://example.org/a.png)"


def test_an_inline_data_image_keeps_only_its_description() -> None:
    """A base64 picture would bloat the note without being readable."""
    html = '<p>Before <img src="data:image/png;base64,AAAA" alt="chart"> after</p>'

    assert html_to_text(html) == "Before chart after"


def test_a_canvas_relative_link_keeps_its_path() -> None:
    """Canvas links its own files by path; the path still names them."""
    html = '<a href="/courses/1/files/2">the file</a>'

    assert html_to_text(html) == "[the file](/courses/1/files/2)"


def test_an_anchor_with_no_usable_address_keeps_only_its_words() -> None:
    """No address, a script or a page jump gives a reader nothing to follow."""
    html = '<a>plain</a> <a href="javascript:void(0)">script</a> <a href="#top">top</a>'

    assert html_to_text(html) == "plain script top"


def test_a_relative_link_becomes_the_schools_address() -> None:
    """A Canvas path means nothing here; with the school's address it still goes somewhere."""
    html = '<a href="/courses/1/files/2">x</a>'

    assert (
        html_to_text(html, "https://school.edu")
        == "[x](https://school.edu/courses/1/files/2)"
    )


def test_a_relative_image_becomes_the_schools_address() -> None:
    """A picture's path is as relative as a link's."""
    html = '<img src="/courses/1/files/2/preview" alt="chart">'

    assert (
        html_to_text(html, "https://school.edu")
        == "![chart](https://school.edu/courses/1/files/2/preview)"
    )


def test_an_absolute_link_is_left_alone_when_a_base_is_given() -> None:
    """Only a path with no host needs one."""
    html = '<a href="https://example.org/x">x</a> <a href="//cdn.example.org/y">y</a>'

    assert (
        html_to_text(html, "https://school.edu")
        == "[x](https://example.org/x) [y](//cdn.example.org/y)"
    )


def test_no_base_leaves_a_relative_link_as_it_is() -> None:
    """The caller that has no school to name changes nothing."""
    html = '<a href="/courses/1/files/2">x</a>'

    assert html_to_text(html) == "[x](/courses/1/files/2)"


def test_two_links_in_one_paragraph_each_keep_their_own_address() -> None:
    """One link's words must not swallow the next link's."""
    html = '<p><a href="https://a.org">A</a> and <a href="https://b.org">B</a></p>'

    assert html_to_text(html) == "[A](https://a.org) and [B](https://b.org)"
