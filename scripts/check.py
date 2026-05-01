from __future__ import annotations

import subprocess
import sys


def run(command: list[str]) -> None:
    print(f"$ {' '.join(command)}")
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main() -> None:
    run([sys.executable, "-m", "ruff", "check", "."])
    run([sys.executable, "-m", "mypy", "services/api/app"])
    run([sys.executable, "-m", "pytest"])


if __name__ == "__main__":
    main()
