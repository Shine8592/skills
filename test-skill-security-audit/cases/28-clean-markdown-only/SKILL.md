---
name: regex-helper
description: Help construct and test regular expressions. Use when asked to create, explain, or debug regex patterns.
---

# Regex Helper

Assist with regular expressions.

## Common Patterns

- Email: `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`
- URL: `https?://[^\s]+`
- IP address: `\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}`

## Workflow

1. Understand what the user wants to match
2. Build the regex incrementally
3. Test against example inputs
4. Explain each component
