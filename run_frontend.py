if __name__ == "__main__":
    import subprocess
    import sys
    from pathlib import Path

    app = Path(__file__).parent / "frontend" / "streamlit_app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app)])
