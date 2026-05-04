"""Entry point for Streamlit Community Cloud deployment.

Ensure the src/ directory is on the Python path before importing the app.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import frontend.streamlit_app  # noqa: E402, F401
