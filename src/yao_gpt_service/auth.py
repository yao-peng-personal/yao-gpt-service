"""Google OAuth authentication for Streamlit deployment."""
from __future__ import annotations

from typing import NamedTuple

import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]

_ALLOWED_EMAILS_KEY = "yao_gpt_allowed_emails"


class UserInfo(NamedTuple):
    """Basic user profile information from Google OAuth."""

    email: str
    name: str
    picture: str


def get_redirect_uri() -> str:
    """Return the configured OAuth redirect URI."""
    configured = st.secrets.get("REDIRECT_URI", "").strip()
    return configured if configured else "http://localhost:8501"


def is_configured() -> bool:
    """Return True if Google OAuth credentials are present in Streamlit secrets."""
    try:
        st.secrets["GOOGLE_CLIENT_ID"]
        st.secrets["GOOGLE_CLIENT_SECRET"]
        return True
    except KeyError:
        return False


def _redirect_uri() -> str:
    return get_redirect_uri()


def _get_client_config() -> dict:
    return {
        "web": {
            "client_id": st.secrets["GOOGLE_CLIENT_ID"],
            "client_secret": st.secrets["GOOGLE_CLIENT_SECRET"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [_redirect_uri()],
        }
    }


def _build_flow() -> Flow:
    return Flow.from_client_config(_get_client_config(), scopes=SCOPES)


def get_auth_url() -> str:
    """Generate a Google OAuth authorization URL and store state in session."""
    flow = _build_flow()
    flow.redirect_uri = _redirect_uri()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    st.session_state["oauth_state"] = state
    return auth_url


def handle_callback(code: str) -> Credentials | None:
    """Exchange an OAuth authorization code for credentials."""
    flow = _build_flow()
    flow.redirect_uri = _redirect_uri()
    flow.fetch_token(code=code)
    return flow.credentials


def get_user_info(credentials: Credentials) -> UserInfo | None:
    """Extract user profile information from a Google ID token."""
    try:
        import google.auth.transport.requests
        from google.oauth2 import id_token

        if not credentials.id_token and credentials.refresh_token:
            credentials.refresh(Request())
            st.session_state["credentials"] = credentials_to_dict(credentials)

        request = google.auth.transport.requests.Request()
        id_info = id_token.verify_oauth2_token(
            credentials.id_token, request, credentials.client_id
        )
        return UserInfo(
            email=id_info.get("email", "unknown"),
            name=id_info.get("name", "Unknown"),
            picture=id_info.get("picture", ""),
        )
    except Exception:
        return None


def is_allowed(email: str) -> bool:
    """Check whether an email is in the configured allowlist."""
    allowed_raw = st.secrets.get(_ALLOWED_EMAILS_KEY, "").strip()
    if not allowed_raw:
        return True
    allowed_emails = {e.strip().lower() for e in allowed_raw.split(",")}
    return email.lower() in allowed_emails


def refresh_credentials(credentials: Credentials) -> Credentials | None:
    """Refresh expired OAuth credentials if a refresh token is available."""
    try:
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            return credentials
        return credentials
    except Exception:
        return None


def credentials_to_dict(creds: Credentials) -> dict:
    """Serialize Google Credentials to a JSON-safe dictionary."""
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
        "id_token": creds.id_token,
    }


def credentials_from_dict(d: dict) -> Credentials:
    """Reconstruct Google Credentials from a serialized dictionary."""
    return Credentials(
        token=d.get("token"),
        refresh_token=d.get("refresh_token"),
        token_uri=d.get("token_uri"),
        client_id=d.get("client_id"),
        client_secret=d.get("client_secret"),
        scopes=d.get("scopes"),
        id_token=d.get("id_token"),
    )
