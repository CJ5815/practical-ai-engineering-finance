"""Week 13: run the same checks CI runs, locally, before you push.

This script exists because of a real incident in this course's own repo:
`ruff check .` failed silently for three weeks (Weeks 10-12) because
nobody ran it locally before pushing — and because it failed first, the
`pytest` step in CI never even ran, hiding a second, separate bug (the
[rag] extra was missing from the CI install step, so every test file
importing chromadb would have failed to collect too). Both were only
found by actually reading `gh run list` and finding two failing runs in a
row.

Run this before every push, not after a red CI run finds it for you:

    python examples/week-13/check_test_health.py
"""

from __future__ import annotations

import subprocess
import sys


def run_check(name: str, command: list[str]) -> bool:
    print(f"=== {name} ===")
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        print(f"FAILED: {name}\n")
        return False
    print(f"OK: {name}\n")
    return True


def main() -> None:
    checks = [
        ("Ruff (lint)", ["ruff", "check", "."]),
        ("Pytest (with coverage)", ["pytest", "--cov=ai_finance_course", "--cov-report=term-missing"]),
    ]

    results = [run_check(name, command) for name, command in checks]

    print("=== Summary ===")
    for (name, _), passed in zip(checks, results):
        print(f"{'PASS' if passed else 'FAIL'}  {name}")

    if not all(results):
        print("\nAt least one check failed — this would also fail in CI. Fix it before pushing.")
        sys.exit(1)

    print("\nAll checks passed — safe to push.")


if __name__ == "__main__":
    main()
