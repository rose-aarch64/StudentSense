import pytest

from modules.canvas.client import CanvasRefusedError, CanvasUnreachableError
from modules.canvas.runlog.stop_code import stop_code
from modules.canvas.sync.connection import NotConnectedError
from modules.egress.service import EgressDeniedError
from modules.embedding.active import EmbeddingNotChosenError
from shared.secrets import UnreadableSecretError


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (NotConnectedError(), "canvas_not_connected"),
        (UnreadableSecretError(), "canvas_token_unreadable"),
        (CanvasRefusedError(), "canvas_token_refused"),
        (CanvasUnreachableError("down"), "canvas_unreachable"),
        (EgressDeniedError("host:school.example"), "egress_disabled"),
        (EmbeddingNotChosenError(), "embedding_not_chosen"),
        (RuntimeError("anything else"), "unknown"),
    ],
)
def test_an_error_that_ends_a_run_has_the_code_the_routes_answer_with(
    error: Exception, code: str
) -> None:
    """The log's last line names why the run stopped, in the routes' own words."""
    assert stop_code(error) == code
