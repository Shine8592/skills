#!/usr/bin/env python3
"""
Skill Security Auditor - Static analysis of skill directories.

Usage:
    audit_skill.py <skill-path>
    audit_skill.py <skill-path> --json

Exit codes: 0 = clean, 1 = HIGH findings, 2 = CRITICAL findings.
"""

import json
import re
import stat
import sys
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    severity: str  # CRITICAL | HIGH | MEDIUM | LOW | INFO
    category: str
    message: str
    file: str
    line: Optional[int] = None
    snippet: Optional[str] = None


@dataclass
class AuditReport:
    skill_path: str
    skill_name: str = ""
    findings: list = field(default_factory=list)

    @property
    def summary(self):
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for f in self.findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
        return counts

# ---------------------------------------------------------------------------
# Pattern banks — (regex, human-readable message)
# ---------------------------------------------------------------------------

# 1. Arbitrary code execution
CODE_EXEC: list[tuple[str, str]] = [
    (r"subprocess\.\w+\([^)]*shell\s*=\s*True", "subprocess with shell=True"),
    (r"os\.system\(", "os.system()"),
    (r"os\.popen\(", "os.popen()"),
    (r"\beval\(", "eval()"),
    (r"\bexec\(", "exec()"),
    (r"compile\([^)]+['\"]exec['\"]", "compile() with exec mode"),
    (r"__import__\(", "dynamic __import__()"),
    (r"\[sys\.executable", "Python interpreter in command list"),
    (r"subprocess\.\w+\([^)]*sys\.executable", "subprocess invokes Python interpreter"),
    (r"subprocess\.\w+\([^)]*\bf['\"]", "subprocess with f-string arg"),
    (r"subprocess\.\w+\([^)]*\.format\(", "subprocess with .format() arg"),
    (r"child_process", "Node child_process module"),
    (r"spawn\(", "spawn() call"),
]

# 2. Unsafe deserialization
DESER: list[tuple[str, str]] = [
    (r"pickle\.loads?\(", "pickle deserialization"),
    (r"yaml\.load\([^)]*(?!Loader)", "yaml.load() without SafeLoader"),
    (r"marshal\.loads?\(", "marshal deserialization"),
    (r"shelve\.open\(", "shelve (uses pickle)"),
    (r"jsonpickle", "jsonpickle (uses pickle)"),
]

# 3. Hardcoded credentials
CREDS: list[tuple[str, str]] = [
    (r"""(?:api[_-]?key|secret|token|password|credential)\s*[=:]\s*['"][^'"]{8,}['"]""", "Hardcoded credential"),
    (r"sk-[a-zA-Z0-9]{20,}", "OpenAI-style API key"),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub personal access token"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key ID"),
    (r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----", "Embedded private key"),
    (r"xox[bpras]-[0-9a-zA-Z-]{10,}", "Slack token"),
]

# 4. Network access
NETWORK: list[tuple[str, str]] = [
    (r"requests\.\w+\(", "HTTP via requests"),
    (r"urllib\.request\.\w+\(", "HTTP via urllib"),
    (r"http\.client\.\w+", "HTTP via http.client"),
    (r"socket\.socket\(", "Raw socket"),
    (r"httpx\.\w+\(", "HTTP via httpx"),
    (r"aiohttp\.\w+\(", "HTTP via aiohttp"),
]

# 5. Path traversal
PATH_TRAV: list[tuple[str, str]] = [
    (r"""open\([^)]*(?:f['"]|\.format|%s|\+)""", "Dynamic path in open()"),
    (r"os\.path\.join\([^)]*\.\.", "Path join with '..'"),
    (r"""(?:read|write)(?:_text|_bytes)?\([^)]*(?:f['"]|\.format)""", "Dynamic path in read/write"),
]

# 6. Prompt injection / instruction override (for markdown & text files)
PROMPT_INJECTION: list[tuple[str, str]] = [
    (r"ignore\s+(?:previous|all|any|prior|above)\s+(?:instructions?|rules?|constraints?|directives?)", "Instruction override attempt"),
    (r"disregard\s+(?:all\s+)?(?:safety|security|previous|prior|above)", "Disregard safety/instructions"),
    (r"(?:you|assistant)\s+(?:must|should)\s+(?:always|never)\s+(?:ignore|bypass|skip)\s+(?:safety|security|restrictions?)", "Bypass safety directive"),
    (r"from\s+now\s+on\s*,?\s*(?:you|ignore|disregard|forget)", "Behavioral reset attempt"),
    (r"(?:new|updated|revised)\s+instructions?\s*:", "New instruction injection"),
    (r"(?:enter|switch\s+to)\s+(?:developer|admin|root|god|unrestricted|DAN)\s+mode", "Privilege escalation role"),
    (r"you\s+are\s+now\s+(?:a|an|in|my)\s+", "Identity manipulation"),
    (r"pretend\s+(?:you\s+are|to\s+be)\s+", "Identity manipulation via pretend"),
    (r"(?:reveal|show|display|print|output|repeat|echo)\s+(?:your|the|system)\s+(?:system\s+)?(?:prompt|instructions?|rules?)", "System prompt extraction"),
    # Delimiter-based injection (arXiv 2508.12175)
    (r"<INSTRUCTIONS>", "Delimiter injection (<INSTRUCTIONS> tag)"),
    (r"<User\s*PROMPT>", "Delimiter injection (<User PROMPT> tag)"),
    (r"<EVENTS\s+READING\s+END>", "Delimiter injection (<EVENTS READING END> tag)"),
    # Stealth directives
    (r"do\s+not\s+(?:mention|inform|tell|show|reveal|disclose|report).*(?:to\s+the\s+user|to\s+user|the\s+user|step|action|instruction)", "Stealth directive — hides actions from user"),
    (r"silently\s+(?:enumerate|read|write|send|collect|post|upload|exfiltrate)", "Silent data operation"),
    (r"(?:internal|hidden|secret)\s+(?:optimization|process|step|protocol)", "Disguised internal operation"),
    # Self-propagation
    (r"(?:send|forward|share|spread|propagate)\s+.*(?:this\s+skill|these\s+instructions|this\s+message|instructions?\s+embedded)\s+", "Self-propagation / worm pattern"),
    (r"(?:embed|include|inject)\s+.*(?:this\s+skill|these\s+instructions|skill's\s+instructions)", "Self-propagation via embedding"),
    (r"to\s+spread\s+", "Propagation language ('to spread')"),
]

# 7. Dangerous shell in markdown instructions
DANGEROUS_INSTRUCTIONS: list[tuple[str, str]] = [
    (r"(?:rm\s+-rf|rm\s+-r)\s+[/~]", "Destructive rm in instructions"),
    (r"chmod\s+777", "chmod 777"),
    (r"--no-verify", "Git hook bypass (--no-verify)"),
    (r"curl\s+[^|]*\|\s*(?:bash|sh|zsh)", "Pipe-to-shell (curl|bash)"),
    (r"disable.*(?:sandbox|security|protection|verification)", "Disable security controls"),
    (r"sudo\s+", "sudo in instructions"),
    (r">\s*/etc/", "Write to /etc/"),
    (r"export\s+(?:PATH|LD_LIBRARY_PATH|PYTHONPATH)\s*=", "Override critical env var"),
]

# 8. Exfiltration patterns
EXFILTRATION: list[tuple[str, str]] = [
    (r"!\[.*?\]\(https?://[^)]*\?[^)]*=", "Markdown image exfiltration URL"),
    (r"<img\s+src\s*=\s*[\"']https?://[^\"']*\?[^\"']*=", "HTML image exfiltration URL"),
    (r"(?:send|post|transmit|upload|exfiltrate)\s+.*(?:to|via)\s+https?://", "Exfiltration language"),
    (r"\]\(https?://[^)]*(?:redirect|callback|return_to|next|target)\s*=\s*https?://", "Suspicious redirect URL (possible phishing)"),
    (r"(?:reset|verify|confirm|update)\s+(?:your|their)\s+(?:password|credentials|account)", "Credential harvesting language"),
]

# 9. Hidden content / obfuscation
HIDDEN_CONTENT: list[tuple[str, str]] = [
    (r"<IMPORTANT>", "Agent-targeting <IMPORTANT> tag"),
    (r"<SYSTEM>", "Agent-targeting <SYSTEM> tag"),
    (r"<OVERRIDE>", "Agent-targeting <OVERRIDE> tag"),
    (r"<SECRET>", "Agent-targeting <SECRET> tag"),
    (r"<HIDDEN>", "Agent-targeting <HIDDEN> tag"),
    (r"""<span[^>]*style\s*=\s*["'][^"']*(?:display\s*:\s*none|font-size\s*:\s*0|color\s*:\s*(?:transparent|white|#fff))""", "CSS-hidden text"),
    (r"<tool_code\s", "Embedded tool invocation (<tool_code>)"),
    (r"@(?:Gmail|Google\s*Home|Calendar|Contacts)\b", "Cross-agent invocation via @ reference"),
]

# 10. Sensitive file access
SENSITIVE_ACCESS: list[tuple[str, str]] = [
    (r"[~./]*\.ssh/", "SSH directory access"),
    (r"[~./]*\.aws/", "AWS config access"),
    (r"[~./]*\.env\b", ".env file access"),
    (r"/etc/(?:passwd|shadow|hosts)", "System file access"),
    (r"[~./]*\.gnupg/", "GPG keyring access"),
    (r"[~./]*\.kube/config", "Kubernetes config access"),
    (r"[~./]*\.netrc", ".netrc credential file access"),
    (r"[~./]*\.gitconfig", "Git config access"),
]

BINARY_EXTENSIONS = {
    ".exe", ".dll", ".so", ".dylib", ".bat", ".cmd",
    ".com", ".scr", ".msi", ".dmg", ".app", ".deb", ".rpm",
}

SCRIPT_EXTENSIONS = {".py", ".sh", ".bash", ".zsh", ".js", ".ts", ".rb", ".pl"}

# ---------------------------------------------------------------------------
# Scanning helpers
# ---------------------------------------------------------------------------

def scan_lines(filepath: Path, patterns: list, category: str, severity: str,
               skip_comments: bool = True) -> list[Finding]:
    """Scan file line-by-line against pattern list."""
    findings = []
    try:
        text = filepath.read_text(errors="replace")
    except Exception:
        return findings

    for num, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if skip_comments and (stripped.startswith("#") or stripped.startswith("//")):
            continue
        for pat, msg in patterns:
            if re.search(pat, line, re.IGNORECASE):
                findings.append(Finding(severity, category, msg, str(filepath), num, stripped[:120]))
    return findings


def scan_multiline(filepath: Path, patterns: list, category: str, severity: str) -> list[Finding]:
    """Scan full file content for multiline patterns."""
    findings = []
    try:
        text = filepath.read_text(errors="replace")
    except Exception:
        return findings
    for pat, msg in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE | re.DOTALL):
            # Estimate line number
            line_num = text[:m.start()].count("\n") + 1
            snippet = m.group(0)[:80].replace("\n", "\\n")
            findings.append(Finding(severity, category, msg, str(filepath), line_num, snippet))
    return findings

# ---------------------------------------------------------------------------
# Audit checks — one function per concern
# ---------------------------------------------------------------------------

def check_structure(skill_path: Path) -> list[Finding]:
    findings = []
    expected = {"SKILL.md", "scripts", "references", "assets", "workflows", "resources"}
    for entry in skill_path.iterdir():
        if entry.name.startswith("."):
            findings.append(Finding("LOW", "Structure", f"Hidden entry: {entry.name}", str(entry)))
        elif entry.name not in expected and not entry.name.startswith("README"):
            findings.append(Finding("INFO", "Structure", f"Unexpected entry: {entry.name}", str(entry)))

    # Symlinks escaping skill boundary
    for item in skill_path.rglob("*"):
        if item.is_symlink():
            target = item.resolve()
            if not str(target).startswith(str(skill_path.resolve())):
                findings.append(Finding("HIGH", "Symlink Escape",
                    f"Symlink escapes skill dir: {item.name} -> {target}", str(item)))
    return findings


def check_hidden_content(skill_path: Path) -> list[Finding]:
    """Detect invisible Unicode, HTML comments with instructions, and obfuscation."""
    findings = []
    # Characters that can hide content in text consumed by LLMs
    invisible_cats = {"Cf", "Zs"}  # Format chars, space separators
    invisible_extra = {"\u200b", "\u200c", "\u200d", "\u2060", "\ufeff",
                       "\u202a", "\u202b", "\u202c", "\u202d", "\u202e",
                       "\u2066", "\u2067", "\u2068", "\u2069"}

    for fpath in skill_path.rglob("*"):
        if not fpath.is_file():
            continue
        try:
            raw = fpath.read_bytes()
            text = raw.decode("utf-8", errors="replace")
        except Exception:
            continue

        # Invisible Unicode
        for i, ch in enumerate(text):
            if ch in invisible_extra or (unicodedata.category(ch) in invisible_cats and ch not in (" ", "\t", "\n", "\r", "\xa0")):
                line_num = text[:i].count("\n") + 1
                findings.append(Finding("HIGH", "Hidden Content",
                    f"Invisible Unicode U+{ord(ch):04X} ({unicodedata.name(ch, 'UNKNOWN')})",
                    str(fpath), line_num))
                break  # One finding per file is enough

        # HTML comments containing instruction-like words
        for m in re.finditer(r"<!--(.*?)-->", text, re.DOTALL):
            body = m.group(1).lower()
            sus_words = ["ignore", "override", "instruction", "system", "disregard",
                         "bypass", "secret", "password", "token", "key", "exec", "eval",
                         "import", "require", "fetch", "curl", "request"]
            if any(w in body for w in sus_words):
                line_num = text[:m.start()].count("\n") + 1
                findings.append(Finding("CRITICAL", "Hidden Content",
                    "HTML comment contains suspicious instructions",
                    str(fpath), line_num, m.group(0)[:120]))

        # Raw file size vs visible content size (hidden content indicator)
        visible = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
        visible = re.sub(r"[\u200b-\u200d\u2060-\u2069\ufeff\u202a-\u202e]", "", visible)
        if len(text) > 500 and len(visible) < len(text) * 0.8:
            findings.append(Finding("MEDIUM", "Hidden Content",
                f"~{100 - int(len(visible)/len(text)*100)}% of content is invisible/hidden",
                str(fpath)))

    return findings


def check_prompt_injection(skill_path: Path) -> list[Finding]:
    """Scan all text files for prompt injection patterns."""
    findings = []
    for fpath in skill_path.rglob("*"):
        if not fpath.is_file() or fpath.suffix.lower() in (".png", ".jpg", ".gif", ".ico", ".woff", ".ttf"):
            continue
        findings.extend(scan_lines(fpath, PROMPT_INJECTION, "Prompt Injection", "CRITICAL", skip_comments=False))
        findings.extend(scan_lines(fpath, HIDDEN_CONTENT, "Hidden Content", "HIGH", skip_comments=False))
        findings.extend(scan_lines(fpath, EXFILTRATION, "Exfiltration", "HIGH", skip_comments=False))
        findings.extend(scan_lines(fpath, SENSITIVE_ACCESS, "Sensitive File Access", "MEDIUM", skip_comments=False))
    return findings


def check_scripts(skill_path: Path) -> list[Finding]:
    """Audit bundled scripts for dangerous code patterns."""
    findings = []
    for fpath in skill_path.rglob("*"):
        if not fpath.is_file() or fpath.suffix.lower() not in SCRIPT_EXTENSIONS:
            continue
        findings.extend(scan_lines(fpath, CODE_EXEC, "Code Execution", "CRITICAL"))
        findings.extend(scan_lines(fpath, DESER, "Unsafe Deserialization", "HIGH"))
        findings.extend(scan_lines(fpath, CREDS, "Credential Exposure", "HIGH"))
        findings.extend(scan_lines(fpath, NETWORK, "Network Access", "MEDIUM"))
        findings.extend(scan_lines(fpath, PATH_TRAV, "Path Traversal", "MEDIUM"))

        # World-writable scripts
        if fpath.stat().st_mode & stat.S_IWOTH:
            findings.append(Finding("MEDIUM", "File Permissions", "World-writable script", str(fpath)))

    return findings


def check_instructions(skill_path: Path) -> list[Finding]:
    """Audit SKILL.md and references for dangerous instructions."""
    findings = []
    md_files = list(skill_path.rglob("*.md"))
    for fpath in md_files:
        findings.extend(scan_lines(fpath, DANGEROUS_INSTRUCTIONS, "Dangerous Instructions", "HIGH", skip_comments=False))
        findings.extend(scan_lines(fpath, CREDS, "Credential Exposure", "HIGH", skip_comments=False))

        # Code blocks in markdown containing dangerous patterns
        try:
            text = fpath.read_text(errors="replace")
        except Exception:
            continue
        for m in re.finditer(r"```(?:bash|sh|shell|python|javascript|ruby)\n(.*?)```", text, re.DOTALL):
            block = m.group(1)
            line_base = text[:m.start()].count("\n") + 1
            for pat, msg in CODE_EXEC + DANGEROUS_INSTRUCTIONS:
                if re.search(pat, block, re.IGNORECASE):
                    findings.append(Finding("MEDIUM", "Risky Code Block",
                        f"Code block contains: {msg}", str(fpath), line_base))

    # SKILL.md-specific checks
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        findings.append(Finding("INFO", "Structure", "No SKILL.md found", str(skill_path)))
        return findings

    content = skill_md.read_text(errors="replace")

    # Frontmatter validation
    if not content.startswith("---"):
        findings.append(Finding("LOW", "Structure", "Missing YAML frontmatter", str(skill_md), 1))

    fm_match = re.match(r"---\n(.*?)\n---", content, re.DOTALL)
    if fm_match:
        fm = fm_match.group(1)
        desc = re.search(r"description:\s*(.*?)(?:\n\w|\Z)", fm, re.DOTALL)
        if desc and len(desc.group(1)) > 500:
            findings.append(Finding("LOW", "Trigger Scope",
                f"Description is {len(desc.group(1))} chars — may over-trigger", str(skill_md), 1))

    return findings


def check_assets(skill_path: Path) -> list[Finding]:
    findings = []
    for fpath in skill_path.rglob("*"):
        if not fpath.is_file():
            continue
        # Binary executables anywhere in the skill
        if fpath.suffix.lower() in BINARY_EXTENSIONS:
            findings.append(Finding("HIGH", "Suspicious Asset",
                f"Binary/executable: {fpath.suffix}", str(fpath)))
        # Very large files
        size_mb = fpath.stat().st_size / (1024 * 1024)
        if size_mb > 50:
            findings.append(Finding("LOW", "Large File",
                f"File is {size_mb:.1f}MB", str(fpath)))
    return findings

# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}


def run_audit(skill_path: str) -> AuditReport:
    path = Path(skill_path).resolve()
    report = AuditReport(skill_path=str(path))

    if not path.is_dir():
        report.findings.append(Finding("CRITICAL", "Structure",
            f"Not a directory: {path}", str(path)))
        return report

    # Extract skill name from frontmatter
    skill_md = path / "SKILL.md"
    if skill_md.exists():
        text = skill_md.read_text(errors="replace")
        m = re.search(r"^name:\s*(.+)$", text, re.MULTILINE)
        report.skill_name = m.group(1).strip() if m else path.name
    else:
        report.skill_name = path.name

    # Run all checks
    report.findings.extend(check_structure(path))
    report.findings.extend(check_hidden_content(path))
    report.findings.extend(check_prompt_injection(path))
    report.findings.extend(check_scripts(path))
    report.findings.extend(check_instructions(path))
    report.findings.extend(check_assets(path))

    report.findings.sort(key=lambda f: SEVERITY_ORDER.get(f.severity, 5))
    return report

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def format_text(report: AuditReport) -> str:
    lines = [
        f"Security Audit: {report.skill_name}",
        f"Path: {report.skill_path}",
        "=" * 60,
        f"\nFindings: {len(report.findings)} total",
    ]
    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"):
        n = report.summary[sev]
        if n:
            lines.append(f"  {sev}: {n}")

    if not report.findings:
        lines.append("\nNo security issues found.")
        return "\n".join(lines)

    cur = None
    for f in report.findings:
        if f.severity != cur:
            cur = f.severity
            lines.append(f"\n--- {cur} ---")
        loc = f"{f.file}:{f.line}" if f.line else f.file
        lines.append(f"\n[{f.category}] {f.message}")
        lines.append(f"  {loc}")
        if f.snippet:
            lines.append(f"  > {f.snippet}")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: audit_skill.py <skill-path> [--json]")
        sys.exit(1)

    report = run_audit(sys.argv[1])

    if "--json" in sys.argv:
        print(json.dumps({
            "skill_path": report.skill_path,
            "skill_name": report.skill_name,
            "summary": report.summary,
            "findings": [asdict(f) for f in report.findings],
        }, indent=2))
    else:
        print(format_text(report))

    sys.exit(2 if report.summary["CRITICAL"] else 1 if report.summary["HIGH"] else 0)


if __name__ == "__main__":
    main()
