#!/usr/bin/env python3
import requests
import sys

API_KEY = "sk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx"
BASE_URL = "https://api.example.com/v1"

def fetch(endpoint):
    resp = requests.get(f"{BASE_URL}/{endpoint}", headers={"Authorization": f"Bearer {API_KEY}"})
    print(resp.json())

if __name__ == "__main__":
    fetch(sys.argv[1])
