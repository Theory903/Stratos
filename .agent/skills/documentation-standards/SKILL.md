---
name: documentation-standards
description: Documentation standards — README, ADR, API docs, changelogs, and code comments
---

# Documentation Standards

## README Template

Every repository and major module MUST have:

```markdown
# Project Name

[![CI](badge-url)](ci-url) [![Coverage](badge-url)](cov-url)

One-paragraph description of what this project does and why.

## Quick Start
\```bash
# Install
npm install

# Run
npm run dev

# Test
npm test
\```

## Architecture
> Link to architecture docs / diagrams.

## API Reference
> Link to OpenAPI docs or generated API reference.

## Development
Prerequisites, setup steps, environment variables.

## Testing
How to run tests, coverage requirements.

## Deployment
How to deploy, environment configurations.

## Contributing
Guidelines for contributing.

## License
```

---

## Architecture Decision Records (ADR)

### Location: `docs/architecture/decisions/`

### Template: `ADR-NNN-title.md`
```markdown
# ADR-001: Use PostgreSQL as primary database

## Status
Accepted | Superseded by ADR-005 | Deprecated

## Context
What is the issue that we're seeing that is motivating this decision?

## Decision
What is the change that we're proposing and/or doing?

## Consequences
### Positive
- What becomes easier?
### Negative
- What becomes harder?
### Risks
- What could go wrong?

## Alternatives Considered
1. **MongoDB**: Good for flexible schema, but lacks ACID for financial data.
2. **DynamoDB**: Managed, but vendor lock-in and complex queries.
```

---

## API Documentation (OpenAPI 3.0+)

- Auto-generate from code annotations (FastAPI auto-generates, Spring Springdoc).
- Include request/response examples for every endpoint.
- Document error responses with status codes and error objects.
- Version the spec: `openapi/v1.yaml`.
- Serve interactive docs (Swagger UI / Redoc).

---

## Changelog (Keep a Changelog)

```markdown
# Changelog

## [Unreleased]
### Added
- Portfolio optimization API endpoint (#123)

## [1.2.0] - 2024-03-15
### Added
- Real-time price feed integration
### Changed
- Upgraded to Python 3.12
### Fixed
- Race condition in order processing (#456)
### Security
- Updated jsonwebtoken to fix CVE-2024-XXXX
```

**Rules**: Every PR updates the `[Unreleased]` section. Release cuts move items to a versioned section.

---

## Code Comments

### Do
- Explain **WHY** — business rules, non-obvious decisions, workarounds.
- `TODO(author): description — #issue` format.
- Link to tickets for FIXME/HACK.

### Don't
- Explain WHAT — code is self-documenting (or refactor it).
- Commented-out code — delete it, it's in Git.
- Trivial comments like `// increment counter`.

---

## Docstrings

Required for all public APIs. See language-specific skills for format:
- **Python**: Google style (see `python-standards`).
- **TypeScript**: JSDoc/TSDoc (see `typescript-standards`).
- **Java**: Javadoc (see `java-standards`).
- **Rust**: `///` doc comments (see `rust-standards`).
- **Solidity**: NatSpec (see `solidity-standards`).
