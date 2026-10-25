from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = ROOT / "frontend" / "dist"
VENV_PYTHON = ROOT / "venv" / "Scripts" / "python.exe"
VENV_PYTHONW = ROOT / "venv" / "Scripts" / "pythonw.exe"
