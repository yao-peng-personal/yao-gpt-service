"""Streamlit chatbot UI with sidebar session management and Google OAuth."""
from __future__ import annotations

import os

import streamlit as st

for key in ("DEEPSEEK_API_KEY", "TAVILY_API_KEY"):
    try:
        if key in st.secrets:
            os.environ[key] = st.secrets[key]
    except Exception:
        pass

st.set_page_config(page_title="Yao GPT", layout="wide")

from yao_gpt_service.auth import (  # noqa: E402
    credentials_from_dict,
    credentials_to_dict,
    get_auth_url,
    get_redirect_uri,
    get_user_info,
    handle_callback,
    is_allowed,
    is_configured,
    refresh_credentials,
)
from yao_gpt_service.config import ModelProvider, settings  # noqa: E402
from yao_gpt_service.crews.chatbot_crew import ChatbotCrew  # noqa: E402
from yao_gpt_service.db.memory import memory  # noqa: E402

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def _check_auth() -> bool:
    if os.environ.get("DISABLE_GOOGLE_AUTH", "").lower() in ("1", "true", "yes"):
        return True

    if not is_configured():
        return True

    if "credentials" in st.session_state:
        credentials = credentials_from_dict(st.session_state["credentials"])
        refreshed = refresh_credentials(credentials)
        if refreshed:
            user = get_user_info(refreshed)
            if user and is_allowed(user.email):
                st.session_state["credentials"] = credentials_to_dict(refreshed)
                st.session_state["user"] = user
                return True

    query_params = st.query_params
    code = query_params.get("code")
    if code:
        try:
            credentials = handle_callback(code)
        except Exception as exc:
            st.error(f"OAuth callback failed: {exc}")
            st.stop()
        if credentials:
            user = get_user_info(credentials)
            if user and is_allowed(user.email):
                st.session_state["credentials"] = credentials_to_dict(credentials)
                st.session_state["user"] = user
                st.query_params.clear()
                st.rerun()
            else:
                email = user.email if user else "unknown"
                st.error(f"Access denied: {email} is not in the allowlist.")
                st.stop()
        else:
            st.error("Failed to authenticate with Google. Please try again.")
            st.stop()

    return False


def _show_login() -> None:
    st.title("Yao GPT")
    st.markdown("### Sign in to continue")
    st.write("This app is private. Please sign in with your Google account.")
    auth_url = get_auth_url()
    st.caption(
        f"Redirect URI: `{get_redirect_uri()}` — "
        "this must match an entry in your Google Cloud Console "
        "→ Credentials → Authorized redirect URIs."
    )
    st.markdown(
        f'<a href="{auth_url}" target="_self">'
        '<button style="padding:12px 24px;font-size:16px;cursor:pointer;'
        "background-color:#4285F4;color:white;border:none;border-radius:4px;"
        '">Sign in with Google</button></a>',
        unsafe_allow_html=True,
    )


if not _check_auth():
    _show_login()
    st.stop()

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

DEFAULTS = {
    "session_id": None,
    "messages": [],
    "provider": settings.default_provider,
    "model": settings.default_model,
    "enable_search": False,
}

for key, default in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default


def start_new_chat() -> None:
    st.session_state.session_id = None
    st.session_state.messages = []
    st.rerun()


def load_session(sid: str) -> None:
    entries = memory.retrieve_recent(sid, n_results=200)
    st.session_state.session_id = sid
    st.session_state.messages = [
        {"role": e.role, "content": e.content} for e in reversed(entries)
    ]
    st.rerun()


def show_sessions() -> None:
    st.rerun()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("Yao GPT")

    user = st.session_state.get("user")
    if user:
        st.caption(f"Signed in as {user.email}")

    if st.button("+ New Chat", use_container_width=True):
        start_new_chat()

    st.divider()

    st.subheader("Provider & Model")
    available = settings.list_models()

    provider_options = [p.value for p in ModelProvider]
    current_provider_idx = provider_options.index(st.session_state.provider.value)
    selected_provider_str = st.selectbox(
        "Provider",
        provider_options,
        index=current_provider_idx,
        key="sidebar_provider",
    )
    st.session_state.provider = ModelProvider(selected_provider_str)

    provider_models = available[st.session_state.provider]
    current_model_idx = (
        provider_models.index(st.session_state.model)
        if st.session_state.model in provider_models
        else 0
    )
    selected_model = st.selectbox(
        "Model",
        provider_models,
        index=current_model_idx,
        key="sidebar_model",
    )
    st.session_state.model = selected_model

    st.session_state.enable_search = st.checkbox(
        "Enable web search",
        value=st.session_state.enable_search,
        key="sidebar_search",
    )

    st.divider()

    st.subheader("Conversations")
    sessions = memory.list_sessions()

    if not sessions:
        st.caption("No conversations yet.")

    for sid in sessions:
        entries = memory.retrieve_recent(sid, n_results=1)
        first_entry = entries[0] if entries else None
        label = first_entry.content[:50] if first_entry else sid

        cols = st.columns([4, 1])
        with cols[0]:
            if st.button(
                label or sid,
                key=f"session_{sid}",
                use_container_width=True,
            ):
                load_session(sid)
        with cols[1]:
            if st.button("🗑", key=f"del_{sid}", help="Delete session"):
                memory.delete_session(sid)
                if st.session_state.session_id == sid:
                    start_new_chat()
                else:
                    show_sessions()


# ---------------------------------------------------------------------------
# Main chat area
# ---------------------------------------------------------------------------

st.title("Yao GPT Service")
st.caption(
    f"Provider: **{st.session_state.provider.value}**  |  "
    f"Model: **{st.session_state.model}**  |  "
    f"Search: **{'on' if st.session_state.enable_search else 'off'}**"
)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Type your message..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            crew = ChatbotCrew(
                provider=st.session_state.provider,
                model=st.session_state.model,
                session_id=st.session_state.session_id,
                enable_search=st.session_state.enable_search,
            )

            history_dicts = st.session_state.messages[-20:]
            result = crew.chat(user_message=prompt, history=history_dicts)

            if st.session_state.session_id is None:
                st.session_state.session_id = result.session_id

            response_text = result.message

        st.markdown(response_text)

    st.session_state.messages.append({"role": "assistant", "content": response_text})
    show_sessions()
