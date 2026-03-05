# Skill Creation Guide

## About Skills

Skills are modular, self-contained packages that extend AI agent capabilities with specialized knowledge, workflows, and tools. They transform a general-purpose agent into a specialized one equipped with procedural knowledge no model fully possesses.

### What Skills Provide

1. **Specialized workflows** — Multi-step procedures for specific domains
2. **Tool integrations** — Instructions for working with specific file formats or APIs
3. **Domain expertise** — Company-specific knowledge, schemas, business logic
4. **Bundled resources** — Scripts, references, and assets for complex and repetitive tasks

## Core Principles

### Conciseness

The context window is a public good. Skills share it with system prompts, conversation history, other skills' metadata, and the user request.

**Default assumption: the agent is already very smart.** Only add context it doesn't already have. Challenge each piece of information: "Does this paragraph justify its token cost?"

Prefer concise examples over verbose explanations.

### Degrees of Freedom

Match specificity to the task's fragility and variability:

- **High freedom** (text-based instructions): Multiple approaches valid, decisions depend on context
- **Medium freedom** (pseudocode/scripts with parameters): Preferred pattern exists, some variation acceptable
- **Low freedom** (specific scripts, few parameters): Operations are fragile, consistency critical

### Progressive Disclosure

Skills use a three-level loading system:

1. **Metadata (name + description)** — Always in context (~100 words)
2. **SKILL.md body** — When skill triggers (keep under 500 lines)
3. **Bundled resources** — As needed (unlimited; scripts can execute without loading into context)

When SKILL.md approaches 500 lines, split content into reference files. Always reference split files from SKILL.md with clear guidance on when to read them.

## Anatomy of a Skill

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (required: name, description)
│   └── Markdown instructions (required)
└── Bundled Resources (optional)
    ├── scripts/      — Executable code (Python/Bash/etc.)
    ├── references/   — Documentation loaded as needed
    └── assets/       — Files used in output (templates, icons, etc.)
```

### SKILL.md

- **Frontmatter** (YAML): `name` and `description` are required. Optional: `license`, `metadata`, `compatibility`. Only `name` and `description` determine when the skill triggers.
- **Body** (Markdown): Instructions and guidance. Only loaded after the skill triggers.

### Scripts (`scripts/`)

Executable code for tasks requiring deterministic reliability or repeatedly rewritten.

### References (`references/`)

Documentation loaded as needed into context. Keep only essential instructions in SKILL.md; move detailed reference material here. Avoid duplication between SKILL.md and references. For files >10k words, include grep patterns in SKILL.md.

### Assets (`assets/`)

Files used in output but not loaded into context (templates, images, fonts, boilerplate).

### What NOT to Include

Do NOT create: README.md, INSTALLATION_GUIDE.md, QUICK_REFERENCE.md, CHANGELOG.md, or any auxiliary documentation.

## Frontmatter Spec

```yaml
---
name: my-skill-name
description: What this skill does and when to use it. Include trigger phrases.
---
```

### `name` (required)
- Kebab-case: lowercase letters, digits, hyphens only (`^[a-z0-9-]+$`)
- 1–64 characters
- Cannot start/end with hyphen or contain consecutive hyphens

### `description` (required)
- Under 1024 characters
- No angle brackets (`<` or `>`)
- Must include BOTH: what the skill does AND when to use it (trigger conditions)
- Include specific tasks users might say and file types if relevant
- All "when to use" info goes here, not in the body

**Good example:**
```yaml
description: Comprehensive document creation, editing, and analysis with support for tracked changes and formatting. Use when working with .docx files for creating documents, modifying content, or working with tracked changes.
```

**Bad examples:**
- Too vague: `description: Helps with projects.`
- Missing triggers: `description: Creates sophisticated multi-page documentation systems.`

## Body Writing Guidelines

- Use imperative/infinitive form ("Run the script", "Create the file")
- Be specific and actionable — include exact commands, file paths, parameters
- Reference all bundled resources from SKILL.md with clear context on when to read them
- Keep one level of reference depth (all reference files linked directly from SKILL.md)
- For reference files >100 lines, include a table of contents

## Creation Process

### 1. Understand the Skill

Clarify concrete usage examples:
- What functionality should the skill support?
- What would a user say to trigger this skill?
- What are example inputs and expected outputs?

### 2. Plan Reusable Contents

For each example, identify what scripts, references, and assets would help when executing the workflow repeatedly.

### 3. Create the Skill Directory

Create the directory with SKILL.md and any needed subdirectories (`scripts/`, `references/`, `assets/`).

### 4. Write SKILL.md and Resources

- Start with reusable resources (scripts, references, assets)
- Write SKILL.md frontmatter with clear name and description
- Write body instructions referencing all bundled resources
- Test any scripts by running them

### 5. Validate

Run the validation script to check frontmatter format, naming conventions, and description constraints.

### 6. Iterate

Use the skill on real tasks, notice inefficiencies, update SKILL.md and resources accordingly.

## Design Patterns

For workflow patterns, see [references/workflows.md](workflows.md).
For output format patterns, see [references/output-patterns.md](output-patterns.md).
