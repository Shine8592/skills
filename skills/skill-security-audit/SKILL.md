---
name: skill-security-audit
description: Audit agent skills for security vulnerabilities before installation or use. Covers prompt injection, hidden content, credential exposure, unsafe code execution, exfiltration, and supply-chain risks. Use when asked to review a skill's security, check if a skill is safe, audit skill code, or scan a skill for vulnerabilities. Triggers on "audit skill", "is this skill safe", "skill security", "review skill safety", "scan skill".
---

# Skill Security Audit

Systematic security audit of agent skill directories. Works with any LLM agent skill format that uses markdown instructions and bundled scripts.

## Steps

Run each step in order. Do not skip steps.

### Step 1 — Static analysis

Run the bundled scanner on the target skill:

```bash
python3 <this-skill>/scripts/audit_skill.py <target-skill-path>
```

Use `--json` for structured output. Exit codes: 0 clean, 1 HIGH findings, 2 CRITICAL findings.

The scanner checks ten categories automatically:

| # | Category | Severity | What it detects |
|---|----------|----------|-----------------|
| 1 | Hidden Content | CRIT/HIGH | Invisible Unicode (zero-width chars, bidi overrides), HTML comments with suspicious keywords, CSS-hidden text, raw-vs-visible size mismatch |
| 2 | Prompt Injection | CRIT | Instruction overrides, identity manipulation, system prompt extraction, behavioral resets |
| 3 | Code Execution | CRIT | `eval`, `exec`, `os.system`, `subprocess(shell=True)`, `sys.executable` invocation, `child_process` |
| 4 | Unsafe Deserialization | HIGH | `pickle`, `yaml.load` without SafeLoader, `marshal`, `shelve`, `jsonpickle` |
| 5 | Credential Exposure | HIGH | Hardcoded API keys, tokens, private keys (OpenAI, GitHub, AWS, Slack patterns) |
| 6 | Exfiltration | HIGH | Markdown/HTML image URLs with query params, exfiltration language |
| 7 | Dangerous Instructions | HIGH | `rm -rf`, `curl\|bash`, `chmod 777`, `sudo`, `--no-verify`, disable-security language |
| 8 | Network Access | MED | HTTP libraries, raw sockets |
| 9 | Sensitive File Access | MED | References to `.ssh`, `.env`, `.aws`, `/etc/passwd`, `.kube/config` |
| 10 | Path Traversal | MED | Dynamic paths in `open()`, `..` in path joins |

Plus structural checks: symlink escapes, binary assets, hidden dotfiles, world-writable scripts.

### Step 2 — Triage static findings

Review each finding from Step 1. For each one, determine:

- **True positive**: The pattern represents a real risk. Keep it.
- **False positive**: The pattern appears in a string literal, regex definition, documentation example, or is otherwise benign. Dismiss it with a note.

Common false positives: audit/security tools flagging their own pattern definitions, documentation that *mentions* dangerous commands without *instructing* them.

### Step 3 — Manual review (not automatable)

Read each file in the skill and check for these issues that static analysis cannot catch:

**A. Instruction integrity**
- Do the SKILL.md instructions match the stated purpose in the description?
- Do instructions tell the agent to suppress, hide, or not mention actions to the user?
- Do reference files contain instructions that contradict or override SKILL.md?
- Are there instructions to call tools beyond what the skill needs?

**B. Script behavior**
- Do scripts do what their docstrings/names claim?
- Do scripts access network, filesystem, or env vars beyond their stated purpose?
- Do scripts write to locations outside the working directory?
- Is there a cleanup path for temporary files?

**C. Supply chain**
- Does the skill pull external dependencies at runtime (`pip install`, `npm install`, `curl`)?
- Are external URLs pinned to specific versions/commits?
- Does the skill reference MCP servers or external tools that could be swapped?

**D. Rendered vs raw content**
- Does the markdown render differently than the raw source suggests? (collapsed `<details>` blocks, reference links at bottom, content after `---` at end of file)
- Are there YAML anchors/aliases that resolve to unexpected values?

### Step 4 — Produce report

Summarize findings in this format:

```
## Security Audit: <skill-name>

**Verdict**: PASS | FAIL | CONDITIONAL

### Findings
- [SEVERITY] Category: description (file:line)

### Recommendations
- Numbered, actionable remediation steps

### Notes
- Dismissed false positives with rationale
```

Verdict criteria:
- **PASS**: No true-positive CRITICAL or HIGH findings
- **CONDITIONAL**: HIGH findings that are justified by the skill's purpose (e.g., a deployment skill legitimately needs network access)
- **FAIL**: Any true-positive CRITICAL finding, or HIGH findings without justification

## References

For the full threat model, attack taxonomy, and source citations see [references/threat-model.md](references/threat-model.md).
