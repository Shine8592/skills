# Skill Improvement Rubric

Use this rubric to evaluate skills. Three evaluation layers: spec checks, best practices scoring, and expert review.

## Layer 1: Spec Checks (Pass/Fail)

Each check must pass. Any failure means the skill is not publishable.

| # | Check | Rule |
|---|-------|------|
| 1 | SKILL.md exists | Skill directory must contain a SKILL.md file |
| 2 | Valid frontmatter | File starts with `---`, contains valid YAML, ends with `---` |
| 3 | Has `name` | Frontmatter includes `name` field |
| 4 | Has `description` | Frontmatter includes `description` field |
| 5 | Name conventions | Kebab-case (`^[a-z0-9-]+$`), 1–64 chars, no leading/trailing/consecutive hyphens |
| 6 | Allowed fields only | Only: `name`, `description`, `license`, `allowed-tools`, `metadata`, `compatibility` |
| 7 | Description constraints | String, under 1024 chars, no angle brackets (`<` or `>`) |

## Layer 2: Best Practices Scoring (100 points)

### Deterministic Checks (30 points)

**SKILL.md under 500 lines (15 pts)**
- Pass (15): Body is under 500 lines
- Warn (8): Body is 501–750 lines — consider splitting to references/
- Fail (0): Body exceeds 750 lines

**No XML tags (10 pts)**
- Pass (10): No XML tag patterns in frontmatter or body
- Fail (0): XML/HTML angle brackets found. These are forbidden for security (could inject instructions in system prompt)

**No README.md (5 pts)**
- Pass (5): No README.md in skill directory
- Fail (0): README.md found. All docs go in SKILL.md or references/

### Quality Checks (70 points)

**Description structure (20 pts)**
Evaluate whether description includes:
- What the skill does (clear value proposition)
- When to use it (trigger conditions)
- Specific tasks/phrases users might say
- File types if relevant

Good: "Analyzes Figma design files and generates developer handoff documentation. Use when user uploads .fig files, asks for 'design specs', 'component documentation', or 'design-to-code handoff'."

Bad: "Helps with projects." (too vague, no triggers)

**Instructions are actionable (15 pts)**
- Instructions include specific commands, file paths, parameters
- Not vague ("validate the data") but concrete ("Run `python scripts/validate.py --input {file}`")

**Error handling included (10 pts)**
- Common issues section with specific error messages, causes, and solutions
- Example: "If you see 'Connection refused': 1. Verify server is running 2. Confirm API key 3. Try reconnecting"

**Resources referenced clearly (10 pts)**
- Every file in scripts/, references/, assets/ is mentioned in SKILL.md
- Clear guidance on when to read each reference file

**Trigger phrases in description (10 pts)**
- Description includes specific phrases users would say
- Action keywords, file types, domain terms

**Examples provided (5 pts)**
- Concrete input/output examples showing what a user might say and what happens
- Helps the agent understand desired style and detail level

### Scoring Scale
- **Pass**: Full points — meets the criterion well
- **Warn**: Half points — partially meets, has room for improvement
- **Fail**: Zero points — does not meet the criterion

## Layer 3: Expert Review (Qualitative)

Evaluate these dimensions narratively:

**Progressive disclosure**: Is content appropriately split across SKILL.md and reference files? Does SKILL.md stay focused on core workflow while detailed docs live in references?

**Conciseness**: Does every paragraph justify its token cost? Is information the agent already knows excluded? Could any section be shorter without losing value?

**Freedom calibration**: Are instructions appropriately specific vs. flexible? Fragile operations should have low freedom (exact scripts), while open-ended tasks should allow high freedom (text guidance).

## How to Apply This Rubric

1. Run spec checks first — all must pass before proceeding
2. Score each best practice check (pass/warn/fail), sum points out of 100
3. Write expert review for progressive disclosure, conciseness, and freedom calibration
4. Present findings as a structured report:

```
## Evaluation Report

### Spec Checks
- [PASS/FAIL] Check name: details

### Best Practices Score: XX/100
- [15/15] SKILL.md under 500 lines
- [10/10] No XML tags
- ...

### Expert Review
**Progressive Disclosure**: ...
**Conciseness**: ...
**Freedom Calibration**: ...

### Recommended Changes (priority order)
1. Most impactful change
2. Second most impactful
3. ...
```

5. Prioritize changes by impact: spec failures first, then low-scoring quality checks, then expert review suggestions
