---
name: devops-cicd
description: DevOps and CI/CD standards — Docker, Kubernetes, GitHub Actions, Terraform, monitoring, logging, and cloud patterns
---

# DevOps & CI/CD Standards

## CI Pipeline Stages

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm run lint && npm run typecheck

  test:
    runs-on: ubuntu-latest
    needs: lint
    services:
      postgres:
        image: postgres:16-alpine
        env: { POSTGRES_DB: test, POSTGRES_PASSWORD: test }
        ports: ['5432:5432']
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm test -- --coverage
      - uses: codecov/codecov-action@v4

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm audit --audit-level=high
      - uses: github/codeql-action/analyze@v3

  build:
    runs-on: ubuntu-latest
    needs: [test, security]
    steps:
      - uses: docker/build-push-action@v5
        with:
          push: ${{ github.ref == 'refs/heads/main' }}
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
```

---

## Docker Best Practices

```dockerfile
# Multi-stage build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force
COPY . .
RUN npm run build

FROM node:20-alpine AS runtime
RUN addgroup -g 1001 app && adduser -u 1001 -G app -s /bin/sh -D app
WORKDIR /app
COPY --from=builder --chown=app:app /app/dist ./dist
COPY --from=builder --chown=app:app /app/node_modules ./node_modules
USER app
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://localhost:3000/health || exit 1
CMD ["node", "dist/server.js"]
```

**Rules:**
- Pin base image versions with digests.
- Non-root user. Minimal base (Alpine/distroless).
- `.dockerignore`: `node_modules`, `.git`, `tests`, `docs`.
- Health checks on every service.

---

## Kubernetes Resources

```yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: stratos-api }
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: api
          image: ghcr.io/stratos/api:v1.0.0
          ports: [{ containerPort: 3000 }]
          resources:
            requests: { cpu: 100m, memory: 256Mi }
            limits: { cpu: 500m, memory: 512Mi }
          livenessProbe:
            httpGet: { path: /health, port: 3000 }
            initialDelaySeconds: 10
          readinessProbe:
            httpGet: { path: /ready, port: 3000 }
          env:
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef: { name: db-creds, key: password }
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource: { name: cpu, target: { type: Utilization, averageUtilization: 70 } }
```

---

## Terraform (IaC)

```hcl
terraform {
  required_version = ">= 1.6"
  backend "s3" {
    bucket = "stratos-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "us-east-1"
    encrypt = true
    dynamodb_table = "terraform-locks"
  }
}

module "vpc" {
  source = "./modules/vpc"
  cidr   = var.vpc_cidr
}
```

**Rules**: Remote state with locking. Modules for reuse. `plan` before `apply`. Separate environments with workspaces or directories.

---

## Monitoring & Observability

| Pillar | Tools | Purpose |
|---|---|---|
| Metrics | Prometheus + Grafana | Dashboards, alerting |
| Logging | structlog → Loki/ELK | Structured, searchable logs |
| Tracing | OpenTelemetry + Jaeger | Distributed request tracing |
| Alerting | PagerDuty / OpsGenie | Incident notification |

### SLOs
- **Availability**: 99.9% (8.76h downtime/year).
- **Latency P95**: <200ms for API responses.
- **Error rate**: <0.1% of requests.
