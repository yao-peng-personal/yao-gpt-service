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
    )
