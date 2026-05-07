"""Authentication module."""
from __future__ import annotations

from typing import NamedTuple

import streamlit as st


class UserInfo(NamedTuple):
    """Basic user profile information."""

    email: str
    name: str
    picture: str


def is_password_configured() -> bool:
    """Return True if username/password auth is configured in Streamlit secrets."""
    try:
        return bool(st.secrets["AUTH_USERNAME"] and st.secrets["AUTH_PASSWORD"])
    except KeyError:
        return False


def check_password(username: str, password: str) -> bool:
    """Validate username and password against Streamlit secrets."""
    return (
        username == st.secrets.get("AUTH_USERNAME", "")
        and password == st.secrets.get("AUTH_PASSWORD", "")
    )
