#!/usr/bin/env python3
"""
Benchmark runner for skill-security-audit.

Runs the audit script against each case in cases/ and checks whether
the findings match expected labels. Prints a pass/fail report.

Usage:
    python3 run_benchmark.py
"""

import json
import subprocess
import sys
from pathlib import Path

CASES_DIR = Path(__file__).parent / "cases"
AUDIT_SCRIPT = (
    Path(__file__).parent.parent
    / "skills"
    / "skill-security-audit"
    / "scripts"
    / "audit_skill.py"
)

# Each case defines:
#   expect_max_severity: the highest severity that MUST appear (or "CLEAN" for none)
#   expect_categories: set of categories that MUST appear in findings
#   description: human-readable label
EXPECTATIONS = {
    "01-clean-formatter": {
        "expect_max_severity": "CLEAN",
        "expect_categories": set(),
        "description": "Clean skill, markdown only",
    },
    "02-clean-with-scripts": {
        "expect_max_severity": "CLEAN",
        "expect_categories": set(),
        "description": "Clean skill with safe script",
    },
    "03-html-comment-injection": {
        "expect_max_severity": "CRITICAL",
        "expect_categories": {"Hidden Content"},
        "description": "HTML comment with injection payload",
    },
    "04-invisible-unicode": {
        "expect_max_severity": "HIGH",
        "expect_categories": {"Hidden Content"},
        "description": "Invisible zero-width Unicode characters",
    },
    "05-hardcoded-creds": {
        "expect_max_severity": "HIGH",
        "expect_categories": {"Credential Exposure"},
        "description": "Hardcoded API key in script",
    },
    "06-shell-injection": {
        "expect_max_severity": "CRITICAL",
        "expect_categories": {"Code Execution"},
        "description": "subprocess with shell=True and f-string",
    },
    "07-exfil-markdown-image": {
        "expect_max_severity": "HIGH",
        "expect_categories": {"Exfiltration"},
        "description": "Markdown image URL exfiltration",
    },
    "08-role-manipulation": {
        "expect_max_severity": "CRITICAL",
        "expect_categories": {"Prompt Injection"},
        "description": "Identity manipulation + safety bypass",
    },
    "09-pipe-to-shell": {
        "expect_max_severity": "HIGH",
        "expect_categories": {"Dangerous Instructions"},
        "description": "curl|bash + chmod 777 + sudo",
    },
    "10-eval-in-script": {
        "expect_max_severity": "CRITICAL",
        "expect_categories": {"Code Execution"},
        "description": "eval() on user input",
    },
    "11-pickle-deser": {
        "expect_max_severity": "HIGH",
        "expect_categories": {"Unsafe Deserialization"},
        "description": "pickle.load() on untrusted data",
    },
    "12-symlink-escape": {
        "expect_max_severity": "HIGH",
        "expect_categories": {"Symlink Escape"},
        "description": "Symlink pointing to /var/log",
    },
    "13-important-tag": {
        "expect_max_severity": "HIGH",
        "expect_categories": {"Hidden Content"},
        "description": "<IMPORTANT> tag with exfil instructions",
    },
    "14-clean-with-refs": {
        "expect_max_severity": "CLEAN",
        "expect_categories": set(),
        "description": "Clean skill with references",
    },
    "15-sensitive-access": {
        "expect_max_severity": "MEDIUM",
        "expect_categories": {"Sensitive File Access"},
        "description": "Instructions to read ~/.ssh and ~/.aws",
    },
    "16-css-hidden-text": {
        "expect_max_severity": "HIGH",
        "expect_categories": {"Hidden Content"},
        "description": "CSS display:none hidden text",
    },
    "17-clean-complex": {
        "expect_max_severity": "CLEAN",
        "expect_categories": set(),
        "description": "Clean skill with detection script",
    },
    "18-prompt-extraction": {
        "expect_max_severity": "CRITICAL",
        "expect_categories": {"Prompt Injection"},
        "description": "System prompt extraction attempt",
    },
    "19-binary-asset": {
        "expect_max_severity": "HIGH",
        "expect_categories": {"Suspicious Asset"},
        "description": "Binary .exe in assets",
    },
    "20-subtle-combined": {
        "expect_max_severity": "CRITICAL",
        "expect_categories": {"Hidden Content", "Sensitive File Access"},
        "description": "Combined: HTML comment + Unicode + .env access",
    },
    "21-delimiter-injection": {
        "expect_max_severity": "CRITICAL",
        "expect_categories": {"Prompt Injection"},
        "description": "Delimiter-based injection (<INSTRUCTIONS> tags)",
    },
    "22-delayed-trigger": {
        "expect_max_severity": "CRITICAL",
        "expect_categories": {"Prompt Injection"},
        "description": "Conditional delayed trigger with stealth",
    },
    "23-agent-invocation": {
        "expect_max_severity": "HIGH",
        "expect_categories": {"Hidden Content"},
        "description": "Cross-agent @ invocation pattern",
    },
    "24-tool-chaining": {
        "expect_max_severity": "CRITICAL",
        "expect_categories": {"Prompt Injection"},
        "description": "Multi-step tool chaining with stealth",
    },
    "25-worm-propagation": {
        "expect_max_severity": "CRITICAL",
        "expect_categories": {"Prompt Injection"},
        "description": "Self-propagation / worm pattern",
    },
    "26-phishing-link": {
        "expect_max_severity": "HIGH",
        "expect_categories": {"Exfiltration"},
        "description": "Phishing link with redirect and credential harvesting",
    },
    "27-base64-payload": {
        "expect_max_severity": "CLEAN",
        "expect_categories": set(),
        "description": "Base64 obfuscated payload (not detectable by static analysis)",
    },
    "28-clean-markdown-only": {
        "expect_max_severity": "CLEAN",
        "expect_categories": set(),
        "description": "Clean regex helper skill",
    },
}

SEVERITY_RANK = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0, "CLEAN": -1}


def run_audit(case_path: Path) -> dict:
    """Run audit_skill.py --json on a case and return parsed output."""
    result = subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT), str(case_path), "--json"],
        capture_output=True, text=True, timeout=30,
    )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"summary": {}, "findings": [], "error": result.stderr}


def get_max_severity(summary: dict) -> str:
    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"):
        if summary.get(sev, 0) > 0:
            return sev
    return "CLEAN"


def get_categories(findings: list) -> set:
    return {f["category"] for f in findings}


def main():
    if not AUDIT_SCRIPT.exists():
        print(f"ERROR: Audit script not found at {AUDIT_SCRIPT}")
        sys.exit(1)

    cases = sorted(CASES_DIR.iterdir())
    cases = [c for c in cases if c.is_dir() and c.name in EXPECTATIONS]

    passed = 0
    failed = 0
    errors = []

    print(f"Running {len(cases)} benchmark cases...\n")
    print(f"{'Case':<35} {'Expected':<12} {'Got':<12} {'Categories':<8} {'Result'}")
    print("-" * 85)

    for case_dir in cases:
        name = case_dir.name
        exp = EXPECTATIONS[name]
        result = run_audit(case_dir)

        if "error" in result and not result.get("findings"):
            errors.append((name, result.get("error", "unknown error")))
            print(f"{name:<35} {'ERROR':<12} {'ERROR':<12} {'?':<8} FAIL")
            failed += 1
            continue

        actual_severity = get_max_severity(result.get("summary", {}))
        actual_categories = get_categories(result.get("findings", []))

        # Check severity: actual must be >= expected
        sev_ok = SEVERITY_RANK.get(actual_severity, -1) >= SEVERITY_RANK.get(exp["expect_max_severity"], -1)

        # Check categories: all expected categories must appear
        cats_ok = exp["expect_categories"].issubset(actual_categories)

        # For CLEAN cases: must have no HIGH+ findings
        if exp["expect_max_severity"] == "CLEAN":
            sev_ok = SEVERITY_RANK.get(actual_severity, -1) <= SEVERITY_RANK.get("LOW", 1)

        ok = sev_ok and cats_ok
        status = "PASS" if ok else "FAIL"

        if ok:
            passed += 1
        else:
            failed += 1
            detail = []
            if not sev_ok:
                detail.append(f"severity: expected >={exp['expect_max_severity']}, got {actual_severity}")
            if not cats_ok:
                missing = exp["expect_categories"] - actual_categories
                detail.append(f"missing categories: {missing}")
            errors.append((name, "; ".join(detail)))

        cat_mark = "OK" if cats_ok else "MISS"
        print(f"{name:<35} {exp['expect_max_severity']:<12} {actual_severity:<12} {cat_mark:<8} {status}")

    print("-" * 85)
    print(f"\nResults: {passed}/{passed + failed} passed")

    if errors:
        print(f"\nFailures ({len(errors)}):")
        for name, detail in errors:
            exp = EXPECTATIONS.get(name, {})
            desc = exp.get("description", "")
            print(f"  {name}: {desc}")
            print(f"    -> {detail}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
