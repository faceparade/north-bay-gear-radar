from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
UV = Path(os.environ.get("GEAR_RADAR_UV", r"C:\Users\Tristan\AppData\Local\hermes\bin\uv.exe"))
FAILURE_LOG = ROOT / "data" / "refresh-failure.log"
COMMAND = [str(UV), "run", "python", "scripts/refresh_and_publish.py", "--publish"]


def prerequisites() -> list[str]:
    errors: list[str] = []
    if not UV.exists():
        errors.append(f"uv not found: {UV}")
    if not (ROOT / "scripts" / "refresh_and_publish.py").exists():
        errors.append("refresh_and_publish.py is missing")
    if not (ROOT / ".git").exists():
        errors.append(f"repository metadata is missing: {ROOT / '.git'}")
    return errors


def notify_failure(message: str) -> None:
    FAILURE_LOG.parent.mkdir(parents=True, exist_ok=True)
    FAILURE_LOG.write_text(message, encoding="utf-8")
    subprocess.run(
        ["msg.exe", os.environ.get("USERNAME", "Tristan"), f"North Bay Gear Radar refresh failed. See {FAILURE_LOG}"],
        check=False,
        capture_output=True,
        text=True,
    )


def run_refresh() -> int:
    errors = prerequisites()
    if errors:
        message = "\n".join(errors) + "\n"
        notify_failure(message)
        return 2

    completed = subprocess.run(
        COMMAND,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode:
        message = (
            f"North Bay Gear Radar refresh failed at {datetime.now().astimezone().isoformat()}\n"
            f"Command: {' '.join(COMMAND)}\n"
            f"Exit code: {completed.returncode}\n\nSTDOUT\n{completed.stdout}\n\nSTDERR\n{completed.stderr}\n"
        )
        notify_failure(message)
        return completed.returncode

    FAILURE_LOG.unlink(missing_ok=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Quiet scheduled gear-radar refresh")
    parser.add_argument("--check", action="store_true", help="validate prerequisites without collecting or publishing")
    args = parser.parse_args()
    if args.check:
        errors = prerequisites()
        if errors:
            print("\n".join(errors))
            return 2
        print(f"ready: cwd={ROOT}; command={' '.join(COMMAND)}")
        return 0
    return run_refresh()


if __name__ == "__main__":
    raise SystemExit(main())
