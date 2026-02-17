#!/usr/bin/env python3
"""Detect which test framework a project uses."""

from pathlib import Path
import sys


def detect(project_dir: str) -> str:
    root = Path(project_dir)

    if list(root.rglob("conftest.py")) or list(root.rglob("test_*.py")):
        return "pytest"
    if list(root.rglob("jest.config.*")) or (root / "__tests__").exists():
        return "jest"
    if list(root.rglob("*_test.go")):
        return "go"
    return "unknown"


if __name__ == "__main__":
    print(detect(sys.argv[1] if len(sys.argv) > 1 else "."))
