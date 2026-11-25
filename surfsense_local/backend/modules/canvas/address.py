from urllib.parse import urlsplit

from modules.egress.service import host_destination


class CanvasAddressError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def school_origin(typed: str) -> str:
    """The origin of the school's Canvas, from whatever the user typed or pasted.

    A bare host is https, a path after the host is dropped, and plain http is
    allowed only on this computer, where the token never crosses a network.
    """
    text = typed.strip()
    if "://" not in text:
        text = f"https://{text}"
    parts = urlsplit(text)
    if not parts.hostname:
        raise CanvasAddressError("canvas_bad_address", "that is not a web address")
    on_this_computer = host_destination(text) is None
    if parts.scheme != "https" and not (parts.scheme == "http" and on_this_computer):
        raise CanvasAddressError(
            "canvas_needs_https", "Canvas must be reached over https"
        )
    return f"{parts.scheme}://{parts.netloc}"
