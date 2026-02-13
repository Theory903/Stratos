# STRATOS — Financial Intelligence OS

> A unified financial–macro–geopolitical intelligence engine designed to quantify uncertainty across scales.

[![CI](https://github.com/theory903/Stratos/actions/workflows/ci.yml/badge.svg)](https://github.com/theory903/Stratos/actions)

## Architecture

STRATOS is a polyglot monorepo with **5 architecture layers**:

| Layer | Technology | Purpose |
|---|---|---|
| **Data Fabric** | Python / FastAPI | Ingestion, storage, feature pipeline |
| **Deterministic Engines** | Rust + Java | Portfolio, risk, DCF, Monte Carlo, fiscal, graph |
| **ML / DL Stack** | Python / PyTorch | Statistical, classical ML, deep learning models |
| **NLP & LLM** | Python / Transformers | Sentiment, embeddings, RAG, narrative detection |
| **Agent Orchestrator** | Python / LangChain | LLM agent with tool-calling and structured output |
| **Frontend** | TypeScript / Next.js | Dashboard, visualization, user interface |

### Design Principles

- **Hexagonal Architecture** (Ports & Adapters) in every service
- **SOLID** at every boundary — narrow protocols, strategy patterns, dependency inversion
- **Domain-Driven Design** — pure domain layer with no external dependencies
- **Independent Deployability** — each service is a standalone deployable unit
- **Cross-Language Contracts** — Protobuf + JSON Schema for type safety across Rust/Java/Python/TS

## Quick Start

```bash
# Start infrastructure (Postgres, Redis, Kafka, MinIO)
make dev

# Run all tests
make test

# Build all Docker images
make build
```

## Project Structure

```
stratos/
├── shared/          # Protobuf & JSON Schema contracts
├── data-fabric/     # Layer 1: Data ingestion & storage
├── engines/
│   ├── rust/        # Layer 2: Performance-critical engines (8 crates)
│   └── java/        # Layer 2: Enterprise APIs (Spring Boot)
├── ml/              # Layer 3: ML/DL models
├── nlp/             # Layer 4: NLP & LLM capabilities
├── orchestrator/    # Layer 5: Agent orchestration
├── frontend/        # Next.js dashboard
├── contracts/       # Solidity smart contracts
├── infra/           # Docker, K8s, Terraform
└── docs/            # Architecture docs, ADRs, API specs
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/macro/analyze-country` | POST | Macro regime analysis |
| `/industry/analyze-sector` | POST | Sector-level analysis |
| `/company/analyze` | POST | Corporate analysis |
| `/portfolio/allocate` | POST | Multi-asset allocation |
| `/policy/simulate` | POST | Policy impact simulation |
| `/tax/optimize` | POST | Tax optimization |
| `/geopolitics/simulate` | POST | Geopolitical scenarios |
| `/fraud/scan` | POST | Fraud detection |
| `/regime/current` | GET | Current market regime |

## License

MIT
