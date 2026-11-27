from urllib.parse import urlsplit

from modules.llm.connections.near_host import is_near_host


def props_url(base_url: str) -> str | None:
    """Where a llama-server on this machine or network reports its window, or
    None for any other host.

    A service on the internet has no such route, and asking would send its key
    on a request that can only fail.
    """
    parts = urlsplit(base_url.strip())
    if parts.scheme not in ("http", "https") or not is_near_host(parts.hostname):
        return None
    path = parts.path.rstrip("/")
    root = path[: -len("/v1")] if path.endswith("/v1") else path
    return f"{parts.scheme}://{parts.netloc}{root}/props"
