"""Front silk copy — shared by preview renderer and KiCad generator."""

from __future__ import annotations

from dataclasses import dataclass

from kamae.types import Sensitive


@dataclass(frozen=True, slots=True)
class CardCopy:
    name: str
    roles: tuple[str, ...]
    contacts: tuple[str, ...]
    qr_url: str


DEFAULT_CARD_COPY = CardCopy(
    name="Wataru Manji",
    roles=(
        "Software Engineer",
        "Platform / Observability / AuthN / Private Cloud",
    ),
    contacts=(
        "www.manj.io",
        Sensitive("manji@linux.com"),
        "x.com/_manji0",
        "github.com/manji-0",
    ),
    qr_url="https://vcard.manji.dev",
)


# Backward-compatible module constants
COPY = DEFAULT_CARD_COPY
NAME = COPY.name
ROLES = COPY.roles
CONTACTS = tuple(c.reveal() if isinstance(c, Sensitive) else c for c in COPY.contacts)
QR_URL = COPY.qr_url
