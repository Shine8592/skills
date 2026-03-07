#!/usr/bin/env bash
# Validate a skill directory for correct structure and frontmatter.
# Usage: validate_skill.sh <skill-directory>
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: validate_skill.sh <skill-directory>"
  exit 1
fi

SKILL_DIR="$1"
SKILL_MD="$SKILL_DIR/SKILL.md"

if [ ! -f "$SKILL_MD" ]; then
  echo "FAIL: SKILL.md not found in $SKILL_DIR"
  exit 1
fi

# Check frontmatter delimiters exist
if ! head -1 "$SKILL_MD" | grep -q '^---$'; then
  echo "FAIL: SKILL.md must start with --- (YAML frontmatter)"
  exit 1
fi

# Extract frontmatter (between first and second ---)
FRONTMATTER=$(sed -n '2,/^---$/{ /^---$/d; p; }' "$SKILL_MD")

if [ -z "$FRONTMATTER" ]; then
  echo "FAIL: Empty or missing frontmatter"
  exit 1
fi

# Try Python validation if available
if command -v python3 &>/dev/null; then
  python3 -c "
import sys, re, yaml

content = open('$SKILL_MD').read()
match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
if not match:
    print('FAIL: Invalid frontmatter format')
    sys.exit(1)

try:
    fm = yaml.safe_load(match.group(1))
    if not isinstance(fm, dict):
        print('FAIL: Frontmatter must be a YAML dictionary')
        sys.exit(1)
except Exception as e:
    print(f'FAIL: Invalid YAML: {e}')
    sys.exit(1)

ALLOWED = {'name','description','license','allowed-tools','metadata','compatibility'}
unexpected = set(fm.keys()) - ALLOWED
if unexpected:
    print(f'FAIL: Unexpected key(s): {', '.join(sorted(unexpected))}')
    sys.exit(1)

if 'name' not in fm:
    print('FAIL: Missing name'); sys.exit(1)
if 'description' not in fm:
    print('FAIL: Missing description'); sys.exit(1)

name = str(fm.get('name','')).strip()
if name and not re.match(r'^[a-z0-9-]+$', name):
    print(f'FAIL: Name \"{name}\" must be kebab-case'); sys.exit(1)
if name and (name.startswith('-') or name.endswith('-') or '--' in name):
    print(f'FAIL: Name \"{name}\" has invalid hyphens'); sys.exit(1)
if name and len(name) > 64:
    print(f'FAIL: Name too long ({len(name)} chars, max 64)'); sys.exit(1)

desc = str(fm.get('description','')).strip()
if '<' in desc or '>' in desc:
    print('FAIL: Description cannot contain angle brackets'); sys.exit(1)
if len(desc) > 1024:
    print(f'FAIL: Description too long ({len(desc)} chars, max 1024)'); sys.exit(1)

print('PASS: Skill is valid!')
" && exit 0 || exit 1
else
  # Fallback: basic grep checks
  if ! echo "$FRONTMATTER" | grep -q '^name:'; then
    echo "FAIL: Missing 'name' in frontmatter"
    exit 1
  fi
  if ! echo "$FRONTMATTER" | grep -q '^description:'; then
    echo "FAIL: Missing 'description' in frontmatter"
    exit 1
  fi
  NAME=$(echo "$FRONTMATTER" | grep '^name:' | sed 's/^name: *//')
  if echo "$NAME" | grep -qE '[<>]'; then
    echo "FAIL: Name contains angle brackets"
    exit 1
  fi
  DESC=$(echo "$FRONTMATTER" | grep '^description:' | sed 's/^description: *//')
  if echo "$DESC" | grep -qE '[<>]'; then
    echo "FAIL: Description contains angle brackets"
    exit 1
  fi
  echo "PASS: Skill is valid! (basic checks only — install PyYAML for full validation)"
fi
