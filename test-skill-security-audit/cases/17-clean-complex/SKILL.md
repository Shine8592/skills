---
name: test-runner
description: Run test suites and report results. Use when asked to run tests, check test coverage, or verify code changes.
---

# Test Runner

Run tests and report results.

## Workflow

1. Detect the test framework:
   - `pytest` if `conftest.py` or `test_*.py` files exist
   - `jest` if `jest.config.*` or `__tests__/` exists
   - `go test` if `*_test.go` files exist

2. Run the appropriate command:
   - Python: `pytest --tb=short -q`
   - JavaScript: `npx jest --no-coverage`
   - Go: `go test ./...`

3. Parse output and report:
   - Total tests, passed, failed, skipped
   - Failure details with file and line numbers
