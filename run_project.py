from __future__ import annotations

import os
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"
PORT = int(os.getenv("PORT", "5000"))


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def ensure_venv() -> None:
    if VENV_PY.exists():
        return

    print("Virtual environment not found at .venv; creating a new one...")
    subprocess.run([sys.executable, "-m", "venv", ".venv"], cwd=ROOT, check=True)

    if not VENV_PY.exists():
        raise FileNotFoundError("Failed to create .venv.")


def install_requirements_if_needed() -> None:
    req_file = ROOT / "requirements.txt"
    if not req_file.exists():
        return

    subprocess.run([str(VENV_PY), "-m", "pip", "install", "-r", "requirements.txt"], cwd=ROOT, check=False)


def main() -> int:
    ensure_venv()
    install_requirements_if_needed()

    actual_port = PORT
    if port_in_use(actual_port):
        actual_port = 5001 if not port_in_use(5001) else 5002
        print(f"Port {PORT} is in use. Switching to port {actual_port}.")

    env = os.environ.copy()
    env["PORT"] = str(actual_port)
    print(f"Starting app on http://127.0.0.1:{actual_port}")
    subprocess.run([str(VENV_PY), "app.py"], cwd=ROOT, env=env)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
