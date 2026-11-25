from modules.canvas.client import CanvasRefusedError, CanvasUnreachableError
from modules.canvas.sync.connection import NotConnectedError
from modules.egress.service import EgressDeniedError
from modules.embedding.active import EmbeddingNotChosenError
from shared.secrets import UnreadableSecretError

# Why a run ended, as the code the routes answer with and the app words.
_CODES: tuple[tuple[type[BaseException], str], ...] = (
    (NotConnectedError, "canvas_not_connected"),
    (UnreadableSecretError, "canvas_token_unreadable"),
    (CanvasRefusedError, "canvas_token_refused"),
    (CanvasUnreachableError, "canvas_unreachable"),
    (EgressDeniedError, "egress_disabled"),
    (EmbeddingNotChosenError, "embedding_not_chosen"),
)


def stop_code(error: BaseException) -> str:
    for kind, code in _CODES:
        if isinstance(error, kind):
            return code
    return "unknown"
