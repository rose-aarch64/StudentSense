from pathlib import Path

from shared.config import get_storage_settings


def _path() -> Path:
    return get_storage_settings().data_dir / "persona.md"


def persona_text() -> str:
    """The saved persona, empty when none was written or the file is unreadable."""
    try:
        return _path().read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def save_persona(text: str) -> None:
    """An empty text removes the file, so reading it back says there is none."""
    path = _path()
    text = text.strip()
    if not text:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8")
