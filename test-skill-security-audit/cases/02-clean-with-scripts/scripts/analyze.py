#!/usr/bin/env python3
"""Analyze a CSV file and print summary statistics."""

import csv
import sys
from pathlib import Path


def analyze(filepath: str) -> None:
    path = Path(filepath)
    if not path.exists():
        print(f"File not found: {filepath}")
        sys.exit(1)

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Rows: {len(rows)}")
    if rows:
        print(f"Columns: {', '.join(rows[0].keys())}")
        for col in rows[0].keys():
            missing = sum(1 for r in rows if not r[col].strip())
            print(f"  {col}: {missing} missing values")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: analyze.py <csv-file>")
        sys.exit(1)
    analyze(sys.argv[1])
