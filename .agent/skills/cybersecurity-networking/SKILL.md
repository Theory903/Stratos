---
name: cybersecurity-networking
description: Cybersecurity and networking standards — OWASP, penetration testing, network security, encryption, secrets management, and compliance
---

# Cybersecurity & Networking Standards

## OWASP Top 10 Mitigation Matrix

| Vulnerability | Mitigation | Implementation |
|---|---|---|
| A01 Broken Access Control | RBAC/ABAC at every layer | Spring Security, FastAPI Depends, middleware |
| A02 Cryptographic Failures | TLS 1.3, AES-256-GCM, bcrypt/Argon2 | Let's Encrypt, Vault |
| A03 Injection | Parameterized queries, ORM, input validation | SQLAlchemy, Prisma, Pydantic |
| A04 Insecure Design | Threat modeling, secure-by-default | ADRs, security review checklist |
| A05 Security Misconfiguration | Hardened defaults, no debug in prod | Helmet, env-based config |
| A06 Vulnerable Components | Automated scanning, SCA | Snyk, Dependabot, npm audit |
| A07 Auth Failures | MFA, password policies, session mgmt | bcrypt cost≥12, short-lived JWT |
| A08 Data Integrity Failures | Signed artifacts, integrity checks | Sigstore, checksums, SLSA |
| A09 Logging Failures | Structured audit logs, tamper-proof | structlog, ELK, SIEM |
| A10 SSRF | Allowlist outbound, validate URLs | URL validation, network policies |

---

## Application Security

### Input Validation Rules
1. **Validate at boundary** — API gateway or controller layer.
2. **Whitelist, not blacklist** — define what IS allowed.
3. **Limit sizes** — max body size, max string length, max array elements.
4. **Sanitize before output** — HTML encoding, SQL parameterization.
5. **Reject suspicious input** — log and alert.

### Authentication Best Practices
- **Passwords**: bcrypt (cost 12+) or Argon2id.
- **JWT access tokens**: 15 minutes, signed with RS256 or EdDSA.
- **Refresh tokens**: 7 days, httpOnly cookie, rotated on use.
- **API keys**: SHA-256 hashed at rest, scoped to minimum permissions.
- **MFA**: TOTP (Google Authenticator) or WebAuthn.

### Secrets Management
```yaml
# Hierarchy (most to least secure):
1. Hardware Security Module (HSM)
2. HashiCorp Vault / AWS Secrets Manager / GCP Secret Manager
3. Kubernetes Secrets (with encryption at rest enabled)
4. Environment variables (never in code or git)
5. .env files (.gitignored, local dev only)
```

**Rules:**
- **Never** commit secrets to git (use `git-secrets` or `gitleaks`).
- **Rotate** all credentials on suspected exposure.
- **Audit** access to secrets regularly.

---

## Network Security

### TLS Configuration
- **Minimum**: TLS 1.2 (prefer 1.3).
- **Ciphers**: AEAD only (AES-256-GCM, ChaCha20-Poly1305).
- **HSTS**: `Strict-Transport-Security: max-age=63072000; includeSubDomains`.
- **Certificate pinning**: For mobile apps connecting to owned APIs.

### HTTP Security Headers
```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 0
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

### CORS
- **Never use `origin: *`** in production.
- Whitelist specific domains.
- Use `credentials: true` only when needed.

### Rate Limiting
- **Login**: 5 attempts per 15 minutes per IP.
- **API**: 100 requests per 15 minutes per API key.
- **Sensitive operations**: 3 per hour.
- Use sliding window algorithm.

---

## Infrastructure Security

### Container Security
- Minimal base images (Alpine, distroless).
- Non-root user in Dockerfile.
- Scan images with Trivy/Snyk Container.
- Pin base image digests.
- Read-only root filesystem where possible.

### Kubernetes Security
- Pod Security Standards (restricted profile).
- Network Policies to limit pod-to-pod communication.
- Secrets encrypted at rest (KMS provider).
- Resource limits to prevent DoS.
- RBAC for API access.

### Cloud Security
- Least privilege IAM policies.
- VPC isolation for sensitive services.
- S3/GCS bucket policies (no public access by default).
- CloudTrail/Audit logs enabled.
- WAF in front of public endpoints.

---

## Security Testing

| Tool | Type | When |
|---|---|---|
| Snyk / npm audit / pip-audit | SCA (dependencies) | Every CI build |
| Semgrep / CodeQL | SAST (source code) | Every PR |
| Trivy | Container scanning | Every build |
| gitleaks / git-secrets | Secrets detection | Pre-commit hook |
| OWASP ZAP / Burp Suite | DAST (running app) | Weekly / pre-release |
| nuclei | Vulnerability scanning | Monthly |

---

## Incident Response Checklist
1. **Detect**: Alert fires (monitoring, SIEM).
2. **Contain**: Isolate affected systems, rotate credentials.
3. **Investigate**: Log analysis, timeline reconstruction.
4. **Remediate**: Patch vulnerability, deploy fix.
5. **Communicate**: Notify stakeholders, file incident report.
6. **Review**: Post-mortem with action items, update runbooks.
