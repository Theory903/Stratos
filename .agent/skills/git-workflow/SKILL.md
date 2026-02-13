---
name: git-workflow
description: Git workflow and protocol — branching strategies, conventional commits, PR templates, code review, merge strategies, release management
---

# Git Workflow Standards

## Branching Strategy

### Trunk-Based (Preferred for STRATOS)
```
main ────────●────────●────────●────────●──
              \      /          \      /
               feat/  (short)    fix/  (short)
```

- **Feature branches**: Live ≤ 2 days. Small, focused PRs.
- **Main**: Always deployable. Protected with required reviews + CI.
- **Release branches** (if needed): `release/v1.2` — only hotfixes.

### Branch Naming
```
feat/add-portfolio-api
fix/timezone-calculation
chore/upgrade-deps
docs/api-reference
refactor/split-engine-module
perf/optimize-risk-calc
test/add-integration-tests
```

---

## Conventional Commits

```
<type>(<scope>): <subject>

[optional body]

[optional footer(s)]
```

### Types
| Type | When |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no logic change |
| `refactor` | Neither fix nor feature |
| `perf` | Performance improvement |
| `test` | Adding/updating tests |
| `build` | Build system/dependencies |
| `ci` | CI configuration |
| `chore` | Maintenance tasks |

### Examples
```
feat(portfolio): add risk calculation endpoint

Implements mean-variance optimization using the covariance matrix
from historical price data. Uses Markowitz model.

Closes #142, #145
```

```
fix(auth): prevent token reuse after password change

Previously, JWT tokens remained valid after password change.
Now invalidate all tokens when password is reset.

BREAKING CHANGE: /auth/reset now requires re-authentication
```

### Rules
- Subject: imperative mood, lowercase, no period, ≤72 chars.
- Body: Explain **WHY**, not WHAT. Wrap at 80 chars.
- One logical change per commit.
- No `WIP`, `temp`, `misc` commits on shared branches.

---

## Pull Request Standards

### PR Title
Same as conventional commit: `type(scope): subject`

### PR Description Template
```markdown
## What
Brief description of what changed.

## Why
Link to issue/ticket. Explain motivation.

## How
Key implementation decisions or trade-offs.

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests passing
- [ ] Manual testing steps (if applicable)

## Screenshots (if UI change)
```

### Before Requesting Review
- [ ] CI passes (lint, type-check, tests).
- [ ] Coverage not decreased.
- [ ] Self-reviewed the diff.
- [ ] Documentation updated.
- [ ] No TODO/FIXME without issue link.

---

## Code Review Checklist

### Reviewer Must Check
- [ ] Logic correctness and edge cases.
- [ ] Error handling (no bare catches, context preserved).
- [ ] Security implications (input validation, secrets, auth).
- [ ] Performance implications (N+1 queries, unbounded loops).
- [ ] Naming clarity and consistency.
- [ ] Test quality (not just coverage).
- [ ] Public API compatibility (breaking changes documented).

### Review Etiquette
- **Reviewers**: Ask questions, don't demand. Explain WHY, not just WHAT.
- **Authors**: Don't take reviews personally. Explain decisions in comments.
- **Turnaround**: Review within 4 hours during business hours.
- **Approval**: At least 1 approval from code owner.

---

## Merge Strategy

| Scenario | Strategy | Why |
|---|---|---|
| Feature → main | **Squash merge** | Clean history |
| Release → main | **Merge commit** (`--no-ff`) | Preserve release context |
| Local cleanup | **Rebase** | Clean before PR |
| Hotfix → main | **Merge commit** | Traceability |

**Never force push** to `main` or shared branches.

---

## Release Management

### Semantic Versioning
```
MAJOR.MINOR.PATCH
  │      │      └─ Bug fixes (backward compatible)
  │      └──────── New features (backward compatible)
  └─────────────── Breaking changes
```

### Release Process
1. Create `release/vX.Y.Z` branch from `main`.
2. Update `CHANGELOG.md` — move `[Unreleased]` to `[vX.Y.Z]`.
3. Update version in `package.json` / `pyproject.toml` / `Cargo.toml`.
4. Create PR, merge with `--no-ff`.
5. Tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`.
6. Push tag: `git push origin vX.Y.Z`.
7. CI builds and publishes release artifacts.

---

## Git Hooks

### Pre-commit (format + lint)
```bash
#!/bin/sh
npx lint-staged  # JS/TS
# OR
ruff check --fix . && ruff format .  # Python
# OR
cargo fmt --check && cargo clippy  # Rust
```

### Commit-msg (validate format)
```bash
#!/bin/sh
commit_regex='^(feat|fix|docs|style|refactor|perf|test|build|ci|chore)(\(.+\))?: .{1,72}$'
if ! grep -qE "$commit_regex" "$1"; then
  echo "Invalid commit message format. Use: type(scope): subject"
  exit 1
fi
```

### Tools
- **JS/TS**: husky + lint-staged + commitlint
- **Python**: pre-commit framework
- **Rust**: cargo-husky
