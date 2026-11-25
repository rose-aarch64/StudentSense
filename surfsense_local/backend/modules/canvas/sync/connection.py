from sqlalchemy.orm import Session, sessionmaker

from modules.canvas.consent import require_school
from modules.canvas.models import CanvasConnection
from shared.secrets import decrypt


class NotConnectedError(Exception):
    """No Canvas connection has been made."""


def read_connection(factory: sessionmaker[Session]) -> tuple[str, str]:
    """The school's address and the decrypted token, once the school's host is allowed.

    A session of its own, closed at once, so no lock is held while Canvas is read.
    """
    with factory() as session:
        row = session.get(CanvasConnection, 1)
        if row is None:
            raise NotConnectedError
        require_school(session, row.base_url)
        return row.base_url, decrypt(row.token_ciphertext)
