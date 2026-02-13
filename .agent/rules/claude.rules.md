# STRATOS — Master SWE Rules

> Cross-cutting rules for every interaction. Language/framework details in `.agent/skills/`.

---

## 1. First-Principles Protocol

### Decompose → Research → Evaluate → Build
1. Break into irreducible sub-problems. Challenge assumptions.
2. Define success metrics (latency, correctness, coverage, cost).
3. Evaluate existing: open-source libs, SaaS, existing repo code.
4. **Build from scratch ONLY when**: no solution exists, unique IP needs, perf-critical, or security concern.
5. PoC/benchmark risky components. Estimate complexity. Document trade-offs in ADR.

---

## 2. Planning Mode

Required artifacts **before code**:

### ADR
`docs/architecture/decisions/ADR-NNN-title.md` — Title → Status → Context → Decision → Consequences → Alternatives.

### Diagrams (Mermaid/PlantUML)
Use Case, C4 Context/Component, Sequence, Class, ERD, State, Deployment — choose appropriate subset. Max 15 elements per diagram. Names must match code identifiers.

### HLD (new services/major features)
System decomposition, NFRs (P50/P95/P99 latency, throughput, availability), communication patterns (sync vs async), resilience (circuit breaker, retry, bulkhead), data consistency model.

### LLD (complex modules)
Module responsibility, public API signatures, contracts (pre/post/invariants), data structures with complexity, algorithm pseudo-code with edge cases, concurrency model, error hierarchy.

---

## 3. Code Quality

### SOLID + Principles
**S**ingle Responsibility · **O**pen/Closed · **L**iskov Substitution · **I**nterface Segregation · **D**ependency Inversion · DRY · KISS · YAGNI · Composition > Inheritance · Fail Fast · Least Privilege

### Function Rules
- Max **40 lines**, **4 params**, **3 nesting levels**
- Guard clauses first, happy path last
- Pure functions preferred, no magic numbers

### File Rules
- Max **400 lines**. One public class/interface per file.
- Import order: stdlib → third-party → local (blank-line separated)
- No circular dependencies

---

## 4. Error Handling

1. **Never swallow** — always log or propagate
2. **Catch specific** — no bare `except:` / `catch(Exception)`
3. **Add context** when re-raising — what failed, with what input
4. **Custom hierarchies** — domain exceptions with error codes
5. **Structured responses**: code, message, timestamp, request ID
6. **Recoverable vs fatal** — retry transient, fail fast on permanent

**Patterns**: Result/Either (Rust/TS), Error boundaries (React), Global handlers (Spring/FastAPI/Express)

---

## 5. Security

### Auth
- **Passwords**: bcrypt (≥12) or Argon2id
- **JWT**: 15min access + 7-day httpOnly refresh
- **OAuth2**: PKCE for SPAs/mobile
- **RBAC/ABAC** + API key rotation + hash before storage

### Validation
- Client AND server. Whitelist > blacklist. Sanitize before storage.
- Libraries: Zod (TS), Pydantic (Python), Bean Validation (Java)

### Encryption
TLS 1.3 (transit) · AES-256-GCM (rest) · Secrets in Vault/env, never in code/Git

### OWASP Top 10
Injection→parameterized queries · Broken auth→MFA/session mgmt · Data exposure→encrypt/minimize · XXE→disable · Access control→every layer · Misconfig→hardened defaults · XSS→CSP/encoding · Deserialization→validate types · Known vulns→automated scanning · Logging→structured audit

### Deps
`npm audit` / `pip-audit` / `cargo audit` in CI. Dependabot/Renovate. Lockfiles committed.

---

## 6. Testing

### Pyramid
| Level | % | Speed | Scope |
|---|---|---|---|
| Unit | 70 | <100ms | Function/class |
| Integration | 20 | <5s | Components, DB, APIs |
| E2E | 10 | <30s | Full workflows |

**Coverage**: 80% min, 95%+ critical paths. New code must not decrease.

### Structure
AAA (Arrange→Act→Assert). One concept per test. No logic in assertions.

**Naming**: `test_[method]_[scenario]_[result]` or `should_[result]_when_[scenario]`

**Mocking**: Mock externals, never SUT. Verify interactions. Prefer fakes for complex deps.

### Frameworks
| Lang | Unit | Integration | E2E |
|---|---|---|---|
| Python | pytest | pytest+testcontainers | playwright |
| TS | vitest | vitest+supertest | playwright/cypress |
| Java | JUnit5+AssertJ | SpringBootTest+Testcontainers | playwright |
| Rust | `#[test]` | testcontainers | — |
| Solidity | `forge test` | Hardhat | — |

---

## 7. Git Workflow

### Branches
**main** (protected, PR-only) · Feature: `feat/`, `fix/`, `chore/` · Delete after merge.

### Conventional Commits
```
type(scope): subject  ≤72 chars, imperative, lowercase, no period
body: WHY not WHAT, wrap 80
footer: BREAKING CHANGE:, Closes #123
```
Types: `feat|fix|docs|style|refactor|perf|test|build|ci|chore`
One logical change per commit. No WIP on shared branches.

### PRs
Title=conventional format. Description: what/why/how-to-test. Link issue. CI passing. Coverage maintained. ≥1 approval.

### Merge
Squash for features · `--no-ff` for releases · Rebase for local cleanup · Never force-push shared.

### Hooks
pre-commit: lint+format · commit-msg: validate format · pre-push: unit tests

---

## 8. Documentation

### Comments
Comment WHY, not WHAT. `TODO(author): desc — #issue`. FIXME/HACK must link issue.

### Docstrings
All public APIs: description, params+types, returns, exceptions, example for complex APIs.

### README
Title+badges · Description · Quick start (≤5 commands) · Architecture · API ref · Dev setup · Testing · Deploy · Contributing · License

### API Docs
OpenAPI 3.0+. Request/response examples. Error responses. Versioned with code.

### Changelog
[Keep a Changelog](https://keepachangelog.com/): Added, Changed, Deprecated, Removed, Fixed, Security.

---

## 9. CI/CD & DevOps

### Pipeline
Lint→Build→Unit Tests→Integration→Security Scan→Docker Build→Deploy Staging→E2E→Deploy Prod (manual gate)

### Docker
Multi-stage · Pin versions · Non-root · Health check · `.dockerignore`

### Kubernetes
Resource requests+limits · Liveness+readiness probes · HPA · Secrets via vault · Namespace isolation

### IaC
Terraform/Pulumi · Remote state with locking · Modules · Plan before apply

### Observability
Metrics: Prometheus+Grafana · Logs: structured JSON, ELK/Loki · Traces: OpenTelemetry · Alerts: PagerDuty, SLO-based

---

## 10. STRATOS Stack

| Layer | Technology | Why |
|---|---|---|
| Perf engines | Rust | Zero-cost abstractions |
| Enterprise APIs | Java 21 + Spring Boot | Mature, virtual threads |
| ML/AI pipeline | Python 3.12 + FastAPI | Library ecosystem |
| Frontend/Agents | TypeScript + Next.js | Type safety, SSR |
| Smart contracts | Solidity 0.8.20+ | EVM standard |
| Primary DB | PostgreSQL 15+ + TimescaleDB | Time-series, JSONB |
| Cache | Redis 7+ | Sub-ms latency |
| Search | Elasticsearch / Meilisearch | Full-text + vector |
| Queue | Kafka / NATS | Event-driven |
| Storage | S3-compatible | Cold data, artifacts |

---

## 11. Skill Cross-References

| Domain | Skill |
|---|---|
| Python | `python-standards` |
| TypeScript | `typescript-standards` |
| Java | `java-standards` |
| Rust | `rust-standards` |
| Solidity | `solidity-standards` |
| Next.js | `nextjs-framework` |
| Express/Fastify | `node-api-frameworks` |
| FastAPI | `fastapi-framework` |
| Spring Boot | `spring-boot-framework` |
| AI/ML | `ai-ml-frameworks` |
| Web3 | `web3-blockchain` |
| DB/ORM | `database-orm` |
| Security | `cybersecurity-networking` |
| TUI | `tui-frameworks` |
| Math | `math-scientific` |
| Testing | `testing-standards` |
| DevOps | `devops-cicd` |
| Docs | `documentation-standards` |
| Architecture | `architecture-design` |
| Git | `git-workflow` |

All at `.agent/skills/{name}/SKILL.md`

---

## 12. Code Review Checklist

- [ ] SOLID principles followed
- [ ] Error handling complete (no bare catches, context preserved)
- [ ] Input validation at boundaries
- [ ] No secrets in code
- [ ] Tests added/updated, coverage maintained
- [ ] Docs updated (docstrings, README, API)
- [ ] Naming clear and consistent
- [ ] No unnecessary complexity
- [ ] Performance/security implications considered
- [ ] Backward compatibility (or breaking change documented)
- [ ] Logging for observability
- [ ] DB migrations reversible
- [ ] No TODO/FIXME without issue link
