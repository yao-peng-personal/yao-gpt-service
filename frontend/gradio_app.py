"""Gradio chatbot UI with sidebar session management and authentication."""

from __future__ import annotations

import os

import gradio as gr

from yao_gpt_service.auth import check_password, is_password_configured
from yao_gpt_service.config import ModelProvider, settings
from yao_gpt_service.crews.chatbot_crew import ChatbotCrew, CrewResult
from yao_gpt_service.db.memory import memory

_provider_models = settings.list_models()


def auth_fn(username: str, password: str) -> bool:
    """Authenticate user against configured credentials."""
    if os.environ.get("DISABLE_AUTH", "").lower() in ("1", "true", "yes"):
        return True
    if not is_password_configured():
        return True
    return check_password(username, password)


def create_demo() -> gr.Blocks:
    """Build and return the Gradio Blocks demo."""
    with gr.Blocks(
        title="Yao GPT",
        theme=gr.themes.Soft(),
    ) as demo:
        # ---- State --------------------------------------------------------------
        sid_state = gr.State(None)

        # ---------------------------------------------------------------------------
        # Sidebar (left column)
        # ---------------------------------------------------------------------------
        with gr.Row():
            with gr.Column(scale=3):
                gr.Markdown("# Yao GPT")

                new_chat_btn = gr.Button(
                    "+ New Chat", variant="primary", size="sm"
                )

                with gr.Accordion("Provider & Model", open=True):
                    provider_dd = gr.Dropdown(
                        choices=[p.value for p in ModelProvider],
                        value=settings.default_provider.value,
                        label="Provider",
                        interactive=True,
                    )
                    model_dd = gr.Dropdown(
                        choices=_provider_models[ModelProvider.DEEPSEEK],
                        value=settings.default_model,
                        label="Model",
                        interactive=True,
                    )
                    search_cb = gr.Checkbox(
                        label="Enable web search", value=True
                    )

                with gr.Accordion("Conversations", open=True):
                    session_list = gr.Radio(
                        choices=_list_session_choices(),
                        label="Sessions",
                        interactive=True,
                        elem_classes="session-list",
                    )
                    with gr.Row():
                        load_btn = gr.Button("Load", size="sm")
                        delete_btn = gr.Button(
                            "Delete", variant="stop", size="sm"
                        )

            # -------------------------------------------------------------------
            # Main chat area (right column)
            # -------------------------------------------------------------------
            with gr.Column(scale=9):
                chatbot = gr.Chatbot(
                    label="Yao GPT Service",
                    height=600,
                    avatar_images=(
                        "https://api.dicebear.com/9.x/initials/svg?seed=User",
                        "https://api.dicebear.com/9.x/bottts/svg?seed=Assistant",
                    ),
                )
                msg_input = gr.Textbox(
                    label="Type your message...",
                    placeholder="Ask anything...",
                )

        # ---- Callbacks -----------------------------------------------------------

        def _update_models(provider_value: str) -> gr.Dropdown:
            """Refresh model dropdown when provider changes."""
            provider = ModelProvider(provider_value)
            models = _provider_models.get(provider, [])
            return gr.Dropdown(
                choices=models, value=models[0] if models else None
            )

        provider_dd.change(
            fn=_update_models,
            inputs=[provider_dd],
            outputs=[model_dd],
        )

        def _new_chat() -> tuple:
            """Reset session and clear chat."""
            return None, [], gr.Radio(choices=_list_session_choices())

        new_chat_btn.click(
            fn=_new_chat,
            outputs=[sid_state, chatbot, session_list],
        )

        def _load_session(selected_sid: str | None) -> tuple:
            """Load a saved session into the chat."""
            if not selected_sid:
                return None, []
            entries = memory.retrieve_recent(selected_sid, n_results=200)
            messages = [{"role": e.role, "content": e.content} for e in entries]
            return selected_sid, messages

        load_btn.click(
            fn=_load_session,
            inputs=[session_list],
            outputs=[sid_state, chatbot],
        )

        def _delete_session(
            selected_sid: str | None, current_sid: str | None
        ) -> tuple:
            """Delete a session from storage and refresh the list."""
            if not selected_sid:
                return (
                    current_sid,
                    [],
                    gr.Radio(choices=_list_session_choices()),
                )
            memory.delete_session(selected_sid)
            new_sid = current_sid
            new_messages: list[dict[str, str]] = []
            if current_sid == selected_sid:
                new_sid = None
                new_messages = []
            return (
                new_sid,
                new_messages,
                gr.Radio(choices=_list_session_choices()),
            )

        delete_btn.click(
            fn=_delete_session,
            inputs=[session_list, sid_state],
            outputs=[sid_state, chatbot, session_list],
        )

        def _chat(
            message: str,
            history: list[dict[str, str]],
            session_id: str | None,
            provider_value: str,
            model_value: str,
            enable_search: bool,
        ):
            """Stream a chat response token-by-token through CrewAI."""
            if not message.strip():
                yield (
                    "",
                    session_id,
                    history,
                    gr.Radio(choices=_list_session_choices()),
                )
                return

            crew = ChatbotCrew(
                provider=ModelProvider(provider_value),
                model=model_value,
                session_id=session_id,
                enable_search=enable_search,
            )

            history_dicts = [
                {"role": m["role"], "content": m["content"]}
                for m in history[-20:]
            ]

            new_sid = crew.session_id
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": ""})

            yield (
                "",
                new_sid,
                history,
                gr.Radio(choices=_list_session_choices(), value=new_sid),
            )

            token_queue = crew.chat_stream(
                user_message=message, history=history_dicts
            )

            while True:
                item = token_queue.get()
                if isinstance(item, CrewResult):
                    history[-1]["content"] = item.message
                    yield (
                        "",
                        item.session_id,
                        history,
                        gr.Radio(
                            choices=_list_session_choices(),
                            value=item.session_id,
                        ),
                    )
                    return
                if isinstance(item, Exception):
                    history[-1]["content"] = f"Error: {item}"
                    yield (
                        "",
                        new_sid,
                        history,
                        gr.Radio(
                            choices=_list_session_choices(), value=new_sid
                        ),
                    )
                    return
                history[-1]["content"] += item
                yield (
                    "",
                    new_sid,
                    history,
                    gr.Radio(choices=_list_session_choices(), value=new_sid),
                )

        msg_input.submit(
            fn=_chat,
            inputs=[
                msg_input,
                chatbot,
                sid_state,
                provider_dd,
                model_dd,
                search_cb,
            ],
            outputs=[msg_input, sid_state, chatbot, session_list],
        )

    return demo


def _get_session_label(session_id: str) -> str:
    """Return a human-readable label for a session."""
    first_message = memory.get_first_user_message(session_id)
    if first_message:
        first_message = first_message.strip()
        return first_message[:60] + ("..." if len(first_message) > 60 else "")
    return session_id[:12]


def _list_session_choices() -> list[tuple[str, str]]:
    """Return (label, value) pairs for the session radio list."""
    sessions = memory.list_sessions()
    return [(_get_session_label(sid), sid) for sid in sessions]
