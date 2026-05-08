"""Authentication module."""

from __future__ import annotations

from typing import NamedTuple

from yao_gpt_service.config import settings


class UserInfo(NamedTuple):
    """Basic user profile information."""

    email: str
    name: str
    picture: str


def is_password_configured() -> bool:
    """Return True if username/password auth is configured in environment."""
    return bool(settings.auth_username and settings.auth_password)


def check_password(username: str, password: str) -> bool:
    """Validate username and password against configured credentials."""
    return (
        username == settings.auth_username
        and password == settings.auth_password
    )
