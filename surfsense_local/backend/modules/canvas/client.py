import httpx

TIMEOUT_SECONDS = 30
PAGE_SIZE = 100


class CanvasRefusedError(Exception):
    """Canvas answered 401: the token is wrong, expired or revoked."""


class CanvasNotFoundError(Exception):
    """Canvas answered 404, with the reason it gave, such as a disabled Pages tab."""


class CanvasUnreachableError(Exception):
    """No usable answer: the network failed or Canvas answered something unexpected."""


class CanvasClient:
    """Reads Canvas's REST API with a student's token. It only ever issues GETs."""

    def __init__(self, base_url: str, token: str) -> None:
        self._origin = httpx.URL(base_url)
        self._http = httpx.Client(
            base_url=f"{base_url}/api/v1",
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT_SECONDS,
        )

    def __enter__(self) -> "CanvasClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self._http.close()

    def get_one(self, path: str, params: dict | None = None) -> dict:
        """One object, as Canvas returns it."""
        return self._get(path, params).json()

    def get_all(self, path: str, params: dict | None = None) -> list[dict]:
        """Every item of a listing, following Canvas's `next` links."""
        items: list[dict] = []
        response = self._get(path, {"per_page": PAGE_SIZE, **(params or {})})
        while True:
            items.extend(response.json())
            next_url = response.links.get("next", {}).get("url")
            if not next_url:
                return items
            response = self._get(self._same_origin(next_url))

    def _same_origin(self, url: str) -> str:
        # The token belongs to the school's host; a link cannot send it elsewhere.
        target = httpx.URL(url)
        if (target.scheme, target.host, target.port) != (
            self._origin.scheme,
            self._origin.host,
            self._origin.port,
        ):
            raise CanvasUnreachableError("Canvas linked to another host")
        return url

    def _get(self, path: str, params: dict | None = None) -> httpx.Response:
        try:
            response = self._http.get(path, params=params)
        except httpx.HTTPError as error:
            raise CanvasUnreachableError(type(error).__name__) from error
        if response.status_code == 401:
            raise CanvasRefusedError
        if response.status_code == 404:
            raise CanvasNotFoundError(_message_of(response))
        if not response.is_success:
            raise CanvasUnreachableError(f"Canvas answered {response.status_code}")
        return response


def _message_of(response: httpx.Response) -> str:
    try:
        return str(response.json().get("message", ""))
    except ValueError:
        return ""
