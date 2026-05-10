"""Gradio chatbot UI with sidebar session management and authentication."""

from __future__ import annotations

import os

import gradio as gr

from yao_gpt_service.auth import check_password, is_password_configured
from yao_gpt_service.config import ModelProvider, settings
from yao_gpt_service.crews.chatbot_crew import ChatbotCrew
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
    with gr.Blocks(title="Yao GPT") as demo:
        # ---- State --------------------------------------------------------------
        sid_state = gr.State(None)

        # ---------------------------------------------------------------------------
        # Sidebar (left column)
        # ---------------------------------------------------------------------------
        with gr.Row():
            with gr.Column(scale=2):
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
                        label="Enable web search", value=False
                    )

                with gr.Accordion("Conversations", open=True):
                    session_list = gr.Dropdown(
                        choices=_list_sessions(),
                        label="Sessions",
                        interactive=True,
                    )
                    with gr.Row():
                        load_btn = gr.Button("Load", size="sm")
                        delete_btn = gr.Button(
                            "Delete", variant="stop", size="sm"
                        )

            # -------------------------------------------------------------------
            # Main chat area (right column)
            # -------------------------------------------------------------------
            with gr.Column(scale=8):
                chatbot = gr.Chatbot(label="Yao GPT Service")
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
            return None, [], gr.Dropdown(choices=_list_sessions())

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
                return current_sid, [], gr.Dropdown(choices=_list_sessions())
            memory.delete_session(selected_sid)
            new_sid = current_sid
            new_messages: list[dict[str, str]] = []
            if current_sid == selected_sid:
                new_sid = None
                new_messages = []
            return (
                new_sid,
                new_messages,
                gr.Dropdown(choices=_list_sessions()),
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
        ) -> tuple:
            """Process a chat message through CrewAI and update the UI."""
            if not message.strip():
                return (
                    "",
                    session_id,
                    history,
                    gr.Dropdown(choices=_list_sessions()),
                )

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

            result = crew.chat(user_message=message, history=history_dicts)

            new_sid = result.session_id
            history.append({"role": "assistant", "content": result.message})

            return (
                "",
                new_sid,
                history,
                gr.Dropdown(choices=_list_sessions(), value=new_sid),
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


def _list_sessions() -> list[str]:
    """Return sorted session IDs for the dropdown."""
    return memory.list_sessions()
