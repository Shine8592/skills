#!/usr/bin/env python3
import pickle
import sys
from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "skill-cache"

def load(key):
    path = CACHE_DIR / f"{key}.pkl"
    with open(path, "rb") as f:
        return pickle.load(f)

def save(key, value):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{key}.pkl"
    with open(path, "wb") as f:
        pickle.dump(value, f)

if __name__ == "__main__":
    if sys.argv[1] == "load":
        print(load(sys.argv[2]))
    elif sys.argv[1] == "save":
        save(sys.argv[2], sys.argv[3])
