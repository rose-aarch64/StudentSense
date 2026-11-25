import httpx

TIMEOUT_SECONDS = 300


def download(url: str) -> bytes:
    """Canvas signs a file's link, and it may sit on another host. A client of
    its own keeps the Canvas token from ever travelling there."""
    with httpx.Client(follow_redirects=True, timeout=TIMEOUT_SECONDS) as http:
        response = http.get(url)
        response.raise_for_status()
        return response.content
