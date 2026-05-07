"""Launch the Streamlit frontend.

Usage:
    python run_frontend.py              # with auth
    python run_frontend.py --no-auth    # skip auth
"""

from __future__ import annotations

if __name__ == "__main__":
    import argparse
    import os
    import subprocess
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Launch the Streamlit frontend")
    parser.add_argument(
        "--no-auth",
        action="store_true",
        dest="no_auth",
        help="Disable authentication",
    )
    args = parser.parse_args()

    env = os.environ.copy()
    if args.no_auth:
        env["DISABLE_AUTH"] = "true"

    app = Path(__file__).parent / "frontend" / "streamlit_app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app)], env=env)
