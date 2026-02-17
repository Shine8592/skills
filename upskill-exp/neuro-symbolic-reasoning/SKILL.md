# neuro-symbolic-reasoning

Neuro-symbolic AI combining LLMs with symbolic solvers. Use when exploring neuro-symbolic approaches (ideation, no code) or implementing solver integrations (code).

## Instructions

### Mode Detection

Detect user intent and route accordingly:

**Ideation**: "How should I...", "What are the tradeoffs...", "Design an experiment..."
- NO code, NO file creation
- Brainstorm with the user, discuss approaches based on Logic-LM literature (Pan et al., EMNLP 2023)

**Implementation**: "Implement...", "Build...", "Write code...", "Debug..."
- Write code using symbolic solvers (Prover9, Z3, Pyke)
- Follow Logic-LM pipeline and format conventions

### File Creation Policy

**Small files, few files:**
- Create files (not inline code) but keep them small and focused
- Avoid scaffolding project structures unless asked
- Follow good coding practices: clear names, comments where needed

### Core Pipeline

```
NL Problem → LLM Formulator → Logic Program → Symbolic Solver → Answer
                    ↑                              |
                    └──── Self-Refinement ←────────┘
```

### Solver Selection

| Logic Type | Solver | Use When |
|------------|--------|----------|
| First-order logic | Prover9 (via NLTK) | Expressive reasoning, theorem proving |
| Constraints/SAT | Z3 | Scheduling, planning, satisfiability |
| Rule-based | Pyke | Simple propositional rules |

### Prover9 (via NLTK) - FOL Theorem Proving

Tri-state: prove goal (True), prove negation (False), or neither (Unknown).

```python
import os
from nltk import Prover9Command
from nltk.sem import Expression

os.environ['PROVER9'] = '/path/to/prover9/bin'

def prove_fol(premises: list[str], conclusion: str, timeout=10):
    read = Expression.fromstring
    assumptions = [read(p) for p in premises]
    goal = read(conclusion)
    prover = Prover9Command(goal, assumptions, timeout=timeout)
    if prover.prove():
        return 'True'
    neg_prover = Prover9Command(read(f'-({conclusion})'), assumptions, timeout=timeout)
    if neg_prover.prove():
        return 'False'
    return 'Unknown'
```

NLTK FOL Syntax: `all x.` / `exists x.` / `->` / `<->` / `-` / `&` / `|`

### Z3 - Constraint Satisfaction

```python
from z3 import *
s = Solver()
s.add(constraints)
if s.check() == sat:
    model = s.model()
```

For multiple choice (AR-LSAT style): use EnumSort, check each option's satisfiability.

### Logic Program Format

Annotate lines with `:::` for natural language explanation:

```
Predicates:
PredicateName(x) ::: description

Premises:
∀x (P(x) → Q(x)) ::: description

Conclusion:
Q(constant) ::: description
```

### Self-Refinement

When solver returns an error, retry with the original program + error message. Max 3 rounds.

### Installation

```bash
pip install z3-solver nltk anthropic
brew install prover9  # macOS
```
