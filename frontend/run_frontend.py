"""Launch the Gradio frontend.

Usage:
    python frontend/run_frontend.py              # with auth
    python frontend/run_frontend.py --no-auth    # skip auth
"""

from __future__ import annotations

if __name__ == "__main__":
    import argparse
    import os
    import sys
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(PROJECT_ROOT))

    parser = argparse.ArgumentParser(description="Launch the Gradio frontend")
    parser.add_argument(
        "--no-auth",
        action="store_true",
        dest="no_auth",
        help="Disable authentication",
    )
    args = parser.parse_args()

    if args.no_auth:
        os.environ["DISABLE_AUTH"] = "true"

    from frontend.gradio_app import auth_fn, create_demo

    demo = create_demo()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        auth=auth_fn if not args.no_auth else None,
        pwa=True,
        show_error=True,
        css="""
.session-list { max-height: 360px; overflow-y: auto !important; }
.bubble-row[data-testid="user"] .bubble {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: #fff !important;
    border-radius: 18px 18px 4px 18px !important;
}
.bubble-row[data-testid="assistant"] .bubble {
    background: #f3f4f6 !important;
    border-radius: 18px 18px 18px 4px !important;
}
""",
    )
