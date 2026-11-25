from collections.abc import Iterable

from sqlalchemy.orm import Session

from modules.egress.service import host_destination, refused_named_host

# What the consent prompt words its question by.
PURPOSE = "canvas"


def require_school(session: Session, base_url: str) -> None:
    """Refuses, for the prompt to ask about, a school host not yet allowed."""
    require_hosts(session, [base_url])


def require_hosts(session: Session, urls: Iterable[str]) -> None:
    """Refuses, in one question, every host among `urls` that is not yet allowed.

    A signed file link may sit on a host of its own, so these are asked about
    together before a course is written or any file is fetched.
    """
    refused = []
    asked: set[str | None] = set()
    for url in urls:
        destination = host_destination(url)
        if destination in asked:
            continue
        asked.add(destination)
        refusal = refused_named_host(session, url)
        if refusal is not None:
            refused.append(refusal)
    if refused:
        first = refused[0]
        first.purpose = PURPOSE
        first.hosts = [r.host for r in refused]
        # The refused hosts are recorded off, so Settings lists them to allow.
        session.commit()
        raise first
