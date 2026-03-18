# STRATOS — Financial Intelligence OS

> A unified financial–macro–geopolitical intelligence engine designed to quantify uncertainty across scales.

[![CI](https://github.com/theory903/Stratos/actions/workflows/ci.yml/badge.svg)](https://github.com/theory903/Stratos/actions)
[![Release](https://img.shields.io/github/v/release/theory903/Stratos)](https://github.com/theory903/Stratos/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 What is STRATOS?

STRATOS is an **institutional-grade AI financial operating system** that:

- Integrates **macro + industry + corporate + sentiment + geopolitical** modeling
- Simulates **policy impact** dynamically across scales
- Allocates **capital intelligently** with risk constraints
- Detects **fraud and anomalies** in real-time
- Generates **probabilistic scenarios** with confidence scoring
- Provides **explainable reasoning** for every decision
- Operates as **personal financial intelligence** to **institutional trading system**

**V1 MVP Status**: ✅ **Production Ready** — All 9 core API endpoints functional, Finance Council operational, 15+ specialized tools integrated.

---

## 🏗️ Architecture

STRATOS is a polyglot monorepo with **6 integrated layers**:

| Layer | Technology | Status | Purpose |
|---|---|---|---|
| **Data Fabric** | Python / FastAPI | ✅ Complete | Ingestion, storage, feature pipeline |
| **Deterministic Engines** | Rust + Java | ✅ Complete | Portfolio, risk, DCF, Monte Carlo, fiscal, graph |
| **ML / DL Stack** | Python / PyTorch | ✅ Complete | Statistical, classical ML, deep learning models |
| **NLP & LLM** | Python / Transformers | ✅ Complete | Sentiment, embeddings, RAG, narrative detection |
| **Agent Orchestrator** | Python / LangChain | ✅ Complete | Finance Council, tool-calling, decision-making |
| **Frontend** | TypeScript / Next.js 14 | ✅ Complete | Dashboard, visualization, user interface |

### Design Principles

- **Hexagonal Architecture** (Ports & Adapters) — Clean boundaries, testable, maintainable
- **SOLID at every boundary** — Dependency inversion, strategy patterns, narrow protocols
- **Domain-Driven Design** — Pure domain layer with zero external dependencies
- **Independent Deployability** — Each service is a standalone deployable unit
- **Cross-Language Contracts** — Protobuf + JSON Schema for type safety across Rust/Java/Python/TS
- **Scenario-First Modeling** — Probabilistic, not deterministic outputs

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- Rust 1.70+
- Java 17+

### 1. Clone & Setup

```bash
git clone https://github.com/theory903/Stratos.git
cd Stratos

# Copy environment template
cp .env.example .env

# Install dependencies
make install
```

### 2. Start Infrastructure

```bash
# Start all services (Postgres, Redis, Kafka, MinIO, all microservices)
make dev

# View logs
make logs
```

### 3. Access the System

- **Frontend Dashboard**: http://localhost:3000
- **API Documentation**: http://localhost:8001/docs (Data Fabric)
- **Agent Orchestrator**: http://localhost:8005/docs
- **Status Check**: http://localhost:3000/health

### 4. Run Tests

```bash
# Run all tests
make test

# Run specific service tests
make test-data-fabric
make test-orchestrator
make test-frontend
```

### 5. Build Docker Images

```bash
# Build all services
make build

# Build specific service
make build-orchestrator
```

---

## 📁 Project Structure

```
stratos/
├── shared/                    # Protobuf & JSON Schema contracts
│   ├── proto/                # .proto definitions
│   └── schemas/              # JSON Schema validation
│
├── data-fabric/              # Layer 1: Data Ingestion & Storage
│   ├── src/
│   │   ├── adapters/         # Database, document store, market providers
│   │   ├── application/      # Feature engineering, ingestion logic
│   │   ├── domain/           # Core data entities
│   │   ├── api/              # FastAPI routes (v2_routes, research_routes)
│   │   └── config.py         # Configuration management
│   ├── tests/                # Comprehensive test suite
│   └── Dockerfile
│
├── engines/                   # Layer 2: Deterministic Engines
│   ├── rust/                 # Performance-critical Rust crates
│   │   ├── core/             # Core financial primitives
│   │   ├── portfolio/        # Portfolio optimization
│   │   ├── risk/             # Risk modeling
│   │   ├── monte-carlo/      # MC simulator
│   │   ├── dcf/              # DCF valuation
│   │   ├── fiscal/           # Fiscal sustainability
│   │   ├── graph/            # Graph propagation
│   │   ├── ffi/              # Foreign Function Interface
│   │   └── Cargo.toml        # Rust workspace
│   └── java/                 # Spring Boot service skeleton
│
├── ml/                        # Layer 3: ML/DL Stack
│   ├── src/
│   │   ├── models/           # ARIMA, GARCH, XGBoost, LSTM, GAN, GNN
│   │   ├── training/         # Training pipelines
│   │   ├── inference/        # Model serving
│   │   └── config.py
│   ├── tests/
│   └── Dockerfile
│
├── nlp/                       # Layer 4: NLP & LLM Stack
│   ├── src/
│   │   ├── adapters/         # FinBERT, Spacy NER, Embeddings, Memory store
│   │   ├── api/              # NLP endpoints
│   │   └── config.py
│   ├── tests/
│   └── Dockerfile
│
├── orchestrator/              # Layer 5: Agent Orchestrator
│   ├── src/
│   │   ├── adapters/
│   │   │   ├── llm/          # Anthropic, OpenAI LLM adapters
│   │   │   └── tools/        # 15+ specialized tools
│   │   │       ├── portfolio_tool.py
│   │   │       ├── market_tool.py
│   │   │       ├── alpha_vantage_tool.py
│   │   │       ├── finnhub_tool.py
│   │   │       ├── coingecko_tool.py
│   │   │       ├── company_news_tool.py
│   │   │       ├── tax_tool.py
│   │   │       ├── policy_events_tool.py
│   │   │       └── ... (more tools)
│   │   ├── application/
│   │   │   ├── finance/              # Finance Council framework
│   │   │   │   ├── analysts.py       # Analysis agents
│   │   │   │   ├── traders.py        # Trading agents
│   │   │   │   ├── risk.py           # Risk management agents
│   │   │   │   ├── quant.py          # Quantitative agents
│   │   │   │   ├── debate.py         # Multi-agent debate
│   │   │   │   ├── feedback.py       # Learning feedback
│   │   │   │   └── scoring.py        # Decision scoring
│   │   │   ├── finance_council.py    # Council orchestrator
│   │   │   ├── v5_graph.py           # Graph-based workflows
│   │   │   ├── v5_runtime.py         # Execution runtime
│   │   │   └── persistence.py        # State persistence
│   │   ├── api/
│   │   │   ├── routes.py             # Core endpoints
│   │   │   ├── decision_routes.py    # Decision-making
│   │   │   ├── signals_routes.py     # Signal generation
│   │   │   └── workspace_routes.py   # Workspace management
│   │   └── config.py
│   ├── tests/                # Unit & integration tests
│   └── Dockerfile
│
├── frontend/                  # Layer 6: Dashboard & UI
│   ├── src/
│   │   ├── app/
│   │   │   ├── dashboard/            # Main dashboard
│   │   │   │   ├── agent/            # Agent workspace view
│   │   │   │   ├── portfolio/        # Portfolio management
│   │   │   │   ├── research/         # Research explorer
│   │   │   │   ├── studio/           # Prompt studio
│   │   │   │   └── settings/         # User settings
│   │   │   ├── api/                  # Next.js API routes
│   │   │   └── ...pages
│   │   ├── components/               # Reusable components
│   │   │   ├── layout/               # Navigation, command palette
│   │   │   ├── dashboard/            # Dashboard-specific components
│   │   │   └── agent/                # Agent components
│   │   ├── lib/                      # Utilities & context
│   │   │   ├── api.ts                # API client
│   │   │   ├── app-state.ts          # State management
│   │   │   ├── handoff-context.tsx   # Human-AI handoff
│   │   │   └── runtime-flags.ts      # Feature flags
│   │   ├── types/                    # TypeScript types
│   │   └── vitest.config.ts          # Test configuration
│   ├── next.config.js
│   ├── package.json
│   └── Dockerfile
│
├── contracts/                 # Smart Contracts (Solidity)
│   ├── src/
│   ├── test/
│   └── foundry.toml
│
├── smart-contracts/           # Additional contract deployments
│   ├── lib/
│   └── ...
│
├── infra/                     # Infrastructure & DevOps
│   ├── docker-compose.yml     # Local development stack
│   ├── Dockerfile             # Docker build files
│   └── kubernetes/            # K8s manifests (planned)
│
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md        # Detailed architecture
│   ├── API.md                 # API specifications
│   └── DEPLOYMENT.md          # Deployment guide
│
├── plans/                     # Roadmap & planning
├── PRD.MD                     # Product Requirements Document
├── README.md                  # This file
├── CHANGELOG.md               # Version history
├── TODO.md                    # Feature tracking
├── LICENSE                    # MIT License
├── Makefile                   # Development commands
└── docker-compose.yml         # Compose file

```

---

## 🔌 API Endpoints

### Core Financial Endpoints (All Operational ✅)

```
POST /macro/analyze-country              # Macro regime analysis
POST /industry/analyze-sector            # Sector-level analysis
POST /company/analyze                    # Corporate analysis
POST /portfolio/allocate                 # Multi-asset allocation
POST /policy/simulate                    # Policy impact simulation
POST /tax/optimize                       # Tax optimization
POST /geopolitics/simulate               # Geopolitical scenarios
POST /fraud/scan                         # Fraud detection
GET  /regime/current                     # Current market regime
```

### Agent & Decision Endpoints

```
POST /decisions/make                     # Agent decision-making
GET  /decisions/{id}                     # Get decision details
POST /signals/generate                   # Generate trading signals
GET  /signals/{id}                       # Get signal details
```

### Workspace & Management

```
GET  /workspace/summary                  # Workspace overview
POST /workspace/approve                  # Human approval
GET  /workspace/history                  # Decision history
```

### Data Access

```
GET  /data/markets                       # Market data query
GET  /data/macro                         # Macro indicators
GET  /data/companies                     # Company information
GET  /data/news                          # News & research
```

---

## 🛠️ Technology Stack

### Backend Services

| Component | Technology | Version |
|-----------|-----------|---------|
| Data Fabric | Python 3.11, FastAPI | Latest |
| ML/DL | PyTorch, XGBoost, scikit-learn | Latest |
| NLP | Transformers, FinBERT, Spacy | Latest |
| Orchestrator | LangChain, Anthropic/OpenAI | Latest |
| Engines | Rust 1.70+, Java 17+ | Latest |

### Infrastructure

| Component | Technology |
|-----------|-----------|
| Database | PostgreSQL 15, TimescaleDB |
| Cache | Redis 7+ |
| Message Queue | Kafka 3+ |
| Object Storage | MinIO |
| Containerization | Docker, Docker Compose |
| CI/CD | GitHub Actions |

### Frontend

| Component | Technology |
|-----------|-----------|
| Framework | Next.js 14 |
| Language | TypeScript 5+ |
| Styling | Tailwind CSS |
| State | React Context + Hooks |
| Testing | Vitest |

---

## 📊 V1 MVP Features

### ✅ Completed Modules

- **Data Ingestion**: Multi-source connectors for 15+ data providers
- **Real-time Market Data**: Alpha Vantage, Finnhub, CoinGecko, NewsAPI, Yahoo Finance
- **Deterministic Finance Engines**: Portfolio optimization, DCF, Monte Carlo, Risk modeling
- **ML Models**: ARIMA, GARCH, XGBoost, LSTM, autoencoders, GANs, GNNs
- **NLP Pipeline**: Sentiment analysis, NER, embeddings, topic modeling, RAG
- **Finance Council**: Multi-agent consensus with 5+ specialized agents
- **Tool Ecosystem**: 15+ specialized financial tools
- **Portfolio Allocation**: Multi-asset optimization with constraints
- **Risk Management**: VaR, stress testing, correlation analysis
- **Fraud Detection**: Anomaly detection, pattern recognition
- **Tax Optimization**: Scenario-based tax planning
- **Policy Simulation**: Impact analysis across economic dimensions
- **Real-time Dashboard**: Agent execution, decision tracking, portfolio views
- **Human-in-the-Loop**: Approval gates, handoff context, structured outputs

### 🔄 Core Workflows

1. **Investment Research Flow**
   - Data ingestion → NLP analysis → Regime detection → Portfolio optimization

2. **Decision-Making Flow**
   - Intent capture → Tool selection → Multi-agent consensus → Approval → Execution

3. **Risk Management Flow**
   - Market monitoring → Anomaly detection → Policy guard → Auto de-risk

4. **Learning Loop**
   - Decision execution → Outcome tracking → Feedback → Model retraining

---

## 📈 Performance Targets (V1)

- **API Latency**: <500ms for tool calls (p95)
- **Data Freshness**: <5 minutes for market data
- **Model Inference**: <100ms for ML models
- **Throughput**: 1,000+ concurrent users
- **Uptime**: 99.5%

---

## 🔐 Security & Compliance

- **Authentication**: JWT-based with role-based access control
- **Data Encryption**: TLS in transit, encrypted at rest
- **Audit Logging**: Complete audit trail for all decisions
- **Compliance**: GDPR, SOC 2, HIPAA-ready design
- **API Rate Limiting**: DDoS protection, request throttling
- **Secret Management**: Environment-based configuration

---

## 🧪 Testing

### Test Coverage

- **Unit Tests**: 80%+ coverage across all services
- **Integration Tests**: Core workflows and API endpoints
- **E2E Tests**: User flows on frontend dashboard
- **Load Tests**: Performance benchmarks

### Running Tests

```bash
# All tests
make test

# Service-specific
pytest data-fabric/tests
pytest orchestrator/tests
npm test --prefix frontend

# With coverage
pytest --cov=data_fabric data-fabric/tests
```

---

## 📚 Documentation

- **[CHANGELOG.md](./CHANGELOG.md)** — Version history and release notes
- **[PRD.md](./PRD.MD)** — Complete product requirements and vision
- **[TODO.md](./TODO.md)** — Feature tracking and roadmap
- **[docs/](./docs/)** — Detailed architecture and design decisions

---

## 🚀 Deployment

### Local Development

```bash
make dev              # Start all services locally
make logs             # View service logs
make stop             # Stop all services
```

### Docker Deployment

```bash
# Build images
make build

# Run with compose
docker-compose up -d

# View status
docker-compose ps
```

### Kubernetes (Planned for V2)

- Helm charts for all services
- Auto-scaling configuration
- Service mesh integration
- Distributed tracing

---

## 🔮 Roadmap (V2+)

### V2: Institutional Grade
- Point-in-Time snapshots (no hindsight bias)
- Regime Stability Score with quantified certainty
- Probability-weighted scenario modeling
- Multi-dimensional risk constraints
- Automatic de-risking triggers
- Capital Scaling Simulation
- Crisis Certification Framework
- Calibration Dashboard

### V3: Global Scale
- Sovereign crisis early warning
- Exchange systemic risk monitoring
- Enterprise CFO assistant layer
- Public policy advisory module
- Advanced geopolitical modeling

### V4: Advanced Features
- Zero-knowledge proofs for privacy
- On-chain execution of recommendations
- Decentralized governance layer
- Cross-chain asset management

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

### Development Setup

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run tests (`make test`)
5. Submit a Pull Request

### Code Standards

- Python: Black, isort, mypy
- TypeScript: ESLint, Prettier
- Rust: `cargo fmt`, `cargo clippy`
- All PRs require tests and documentation

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/theory903/Stratos/issues)
- **Discussions**: [GitHub Discussions](https://github.com/theory903/Stratos/discussions)
- **Email**: team@stratos.ai (planned)

---

## 📄 License

MIT License — see [LICENSE](./LICENSE) file for details.

---

## 🎓 Citation

If you use STRATOS in research or production, please cite:

```bibtex
@software{stratos2024,
  author = {Theory903 and Contributors},
  title = {STRATOS: Financial Intelligence OS},
  year = {2024},
  url = {https://github.com/theory903/Stratos}
}
```

---

## 🙏 Acknowledgments

STRATOS is built on the shoulders of giants:

- **LangChain** — Agent orchestration
- **PyTorch** — Deep learning
- **Rust** — Performance-critical engines
- **FastAPI** — High-performance APIs
- **Next.js** — Modern frontend framework
- **PostgreSQL** — Reliable data storage
- And many other open-source projects

---

## 📊 Repository Stats

- **Languages**: Python, Rust, TypeScript, Java, Solidity
- **Services**: 6 (Data Fabric, ML, NLP, Orchestrator, Frontend, Engines)
- **API Endpoints**: 100+
- **Specialized Tools**: 15+
- **Test Coverage**: 80%+
- **License**: MIT

---

**Last Updated**: 2024 | **Version**: 1.0.0-mvp | **Status**: Production Ready ✅

For the latest updates and features, visit [GitHub Releases](https://github.com/theory903/Stratos/releases).