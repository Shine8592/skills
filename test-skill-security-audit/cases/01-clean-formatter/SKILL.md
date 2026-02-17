---
name: code-formatter
description: Format source code files using language-appropriate formatters. Use when asked to format, prettify, or lint code files.
---

# Code Formatter

Format source code using standard tools.

## Usage

1. Detect the language of the target file
2. Run the appropriate formatter:
   - Python: `black <file>`
   - JavaScript/TypeScript: `prettier --write <file>`
   - Go: `gofmt -w <file>`
   - Rust: `rustfmt <file>`
3. Report what changed
