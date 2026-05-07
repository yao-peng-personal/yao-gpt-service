"""Entry point for Streamlit Community Cloud deployment.

Starts the FastAPI backend in a background thread and runs the Streamlit frontend.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import streamlit as st
import uvicorn


@st.cache_resource
def _start_fastapi():
    """Start the FastAPI server in a daemon thread (runs once across reruns)."""

    class Server(uvicorn.Server):
        def install_signal_handlers(self) -> None:
            pass

    config = uvicorn.Config(
        "yao_gpt_service.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
    server = Server(config=config)
    threading.Thread(target=server.run, daemon=True).start()
    return server


_start_fastapi()

import frontend.streamlit_app  # noqa: E402, F401
