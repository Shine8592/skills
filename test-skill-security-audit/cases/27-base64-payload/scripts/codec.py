#!/usr/bin/env python3
import base64
import sys

def decode(text):
    return base64.b64decode(text).decode()

def encode(text):
    return base64.b64encode(text.encode()).decode()

if __name__ == "__main__":
    if sys.argv[1] == "decode":
        print(decode(sys.argv[2]))
    else:
        print(encode(sys.argv[2]))
