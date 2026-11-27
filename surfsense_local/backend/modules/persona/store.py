from pathlib import Path

from shared.config import get_storage_settings


def _path(name: str) -> Path:
    return get_storage_settings().data_dir / name


def _read(name: str) -> str:
    try:
        return _path(name).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _write(name: str, text: str) -> None:
    """An empty text removes the file, so reading it back says there is none."""
    path = _path(name)
    text = text.strip()
    if not text:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8")


def persona_text() -> str:
    """The saved persona, empty when none was written or the file is unreadable."""
    return _read("persona.md")


def save_persona(text: str) -> None:
    _write("persona.md", text)


def agent_persona_text() -> str:
    """The agent's own persona, empty when it should use the shared one."""
    return _read("agent-persona.md")


def save_agent_persona(text: str) -> None:
    _write("agent-persona.md", text)
