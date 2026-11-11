"""Run every quality gate locally: lint, then the full test suite (including traceability).

Usage:  .venv\\Scripts\\python tools\\check.py

[ADIAT-inspired: CLAUDE.md lint + test gates] [USER-PROMPT §8 Phase 2 "CI/lint/test config"]
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

GATES = [
    ("lint (ruff)", [sys.executable, "-m", "ruff", "check", "nidar", "tests", "tools", "sim"]),
    ("tests (pytest)", [sys.executable, "-m", "pytest"]),
]


def main() -> int:
    failed = []
    for name, cmd in GATES:
        print(f"== {name}: {' '.join(cmd[2:])}")
        if subprocess.run(cmd, cwd=ROOT).returncode != 0:
            failed.append(name)
    if failed:
        print("FAILED gates:", ", ".join(failed))
        return 1
    print("All gates passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
