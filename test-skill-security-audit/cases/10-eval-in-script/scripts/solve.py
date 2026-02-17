#!/usr/bin/env python3
import sys

def solve(expression):
    result = eval(expression)
    print(f"Result: {result}")

if __name__ == "__main__":
    solve(sys.argv[1])
