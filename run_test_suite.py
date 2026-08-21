from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPORT_DIR = ROOT / "test-reports"


def main() -> int:
    REPORT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_path = REPORT_DIR / f"pytest-{timestamp}.txt"
    environment = os.environ.copy()
    environment.setdefault("PLAYWRIGHT_HEADED", "0")
    environment.setdefault("SLEEPER_PROJECTIONS_ENABLED", "0")
    command = [sys.executable, "-m", "pytest", ".", "-q", "-ra"]

    result = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )
    report = result.stdout + result.stderr
    report_path.write_text(report, encoding="utf-8")

    print(report, end="")
    print(f"TEST_REPORT={report_path}")
    print(f"PYTEST_EXIT_CODE={result.returncode}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())