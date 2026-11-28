from html.parser import HTMLParser

BLOCK_TAGS = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}


class _TextExtractor(HTMLParser):
    def __init__(self, base_url: str | None = None) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._base = (base_url or "").rstrip("/")
        # The open link's address, and where its words begin in `parts`.
        self._link: tuple[str, int] | None = None

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in BLOCK_TAGS:
            self.parts.append("\n")
        elif tag == "a":
            href = (dict(attrs).get("href") or "").strip()
            if href and not href.startswith("#") and not _is_script(href):
                self._link = (self._absolute(href), len(self.parts))
        elif tag == "img":
            self._image(dict(attrs))

    def handle_endtag(self, tag: str) -> None:
        if tag in BLOCK_TAGS:
            self.parts.append("\n")
        elif tag == "a" and self._link is not None:
            href, start = self._link
            self._link = None
            words = " ".join("".join(self.parts[start:]).split())
            del self.parts[start:]
            # A link's address is worth keeping: it is where the words point.
            self.parts.append(
                href if not words or words == href else f"[{words}]({href})"
            )

    def _image(self, attrs: dict) -> None:
        src = (attrs.get("src") or "").strip()
        alt = " ".join((attrs.get("alt") or "").split())
        if src and not src.lower().startswith("data:"):
            self.parts.append(f"![{alt}]({self._absolute(src)})")
        elif alt:
            # An inline picture's bytes would bloat the note; its description stays.
            self.parts.append(alt)

    def _absolute(self, address: str) -> str:
        # A path with no host is the school's own; a "//host" address is not.
        if self._base and address.startswith("/") and not address.startswith("//"):
            return self._base + address
        return address

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _is_script(href: str) -> bool:
    return href.lower().startswith("javascript:")


def html_to_text(html: str | None, base_url: str | None = None) -> str:
    """Canvas keeps rich text as HTML; a model needs the words, and each link and
    picture in markdown so its address is not lost. A path with no host is made
    the school's address when `base_url` names it."""
    if not html:
        return ""
    extractor = _TextExtractor(base_url)
    extractor.feed(html)
    lines = (line.strip() for line in "".join(extractor.parts).splitlines())
    return "\n".join(line for line in lines if line)
