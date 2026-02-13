# STRATOS — Master Work Plan

> Phased roadmap from scaffolding → MVP → production.
> Each phase is self-contained and shippable.

---

## Phase 0: Foundation & DevOps Bootstrap
> **Goal**: Complete scaffolding, git, CI — the project compiles and runs empty shells.

### 0.1 Complete Scaffolding (Remaining)
- [ ] Finish data-fabric adapters: `postgres.py`, `redis_cache.py`, `s3_store.py`, `kafka_publisher.py`
- [ ] Finish data-fabric source adapters: `market_feed.py`, `macro_fred.py`, `edgar.py`, `news_api.py`
- [ ] Create ML application layer: `train_model.py`, `predict.py`, `detect_regime.py`
- [ ] Create ML API layer: `app.py`, `routes.py`, `deps.py`, `config.py`
- [ ] Create NLP application layer: `score_sentiment.py`, `parse_earnings.py`, `detect_narrative.py`
- [ ] Create NLP API layer: `app.py`, `routes.py`, `deps.py`, `config.py`
- [ ] Create NLP domain entities: `sentiment.py`, `document.py`, `narrative.py`
- [ ] Create Orchestrator application layer: `orchestrate.py`, `plan_tasks.py`, `execute_tool.py`
- [ ] Create Orchestrator API layer: `app.py`, `routes.py`, `deps.py`, `config.py`
- [ ] Create Orchestrator tool stubs: all 9 tool files (`macro_tool.py` → `regime_tool.py`)
- [ ] Create Orchestrator domain entities: `task.py`, `plan.py`, `memo.py`, `confidence.py`
- [ ] Scaffold Java/Spring Boot: `pom.xml`, `EnginesApplication.java`, `SecurityConfig.java`, domain/port/adapter layers
- [ ] Scaffold Frontend: `package.json`, `tsconfig.json`, `next.config.ts`, `layout.tsx`, `page.tsx`, API client
- [ ] Create Dockerfiles: all 7 in `infra/docker/`
- [ ] Create `CHANGELOG.md` and `LICENSE`
- [ ] Create `infra/scripts/setup-dev.sh` and `seed-data.sh`
- [ ] Create `engine_service.proto` in `shared/proto/`
- [ ] Create JSON schemas in `shared/schemas/`
- [ ] Create event schemas in `shared/events/`

### 0.2 Git & GitHub
- [ ] Initialize git repository
- [ ] Create `.github/workflows/ci.yml` (unified CI)
- [ ] Create `.github/workflows/rust.yml`, `python.yml`, `java.yml`, `frontend.yml`
- [ ] Create `.github/PULL_REQUEST_TEMPLATE.md`
- [ ] Create `.github/CODEOWNERS`
- [ ] Push to `theory903/Stratos` public repo

### 0.3 Architecture Documentation
- [ ] Write `ADR-001-monorepo.md` — why polyglot monorepo
- [ ] Write `ADR-002-hexagonal.md` — ports & adapters pattern
- [ ] Write `ADR-003-rust-engines.md` — why Rust for perf-critical engines
- [ ] Write `docs/architecture/C4-context.md`
- [ ] Write `docs/architecture/data-flow.md`
- [ ] Draft initial `docs/api/openapi.yaml`

### 0.4 Dev Environment
- [ ] Verify `docker-compose up` boots Postgres + Redis + Kafka + MinIO
- [ ] Verify `make lint` / `make test` run (even if empty)
- [ ] Verify Rust workspace compiles: `cd engines/rust && cargo check`
- [ ] Set up pre-commit hooks (ruff, clippy, prettier)

---

## Phase 1: Data Fabric (Layer 1)
> **Goal**: Ingest real market data, store in TimescaleDB, serve via API.

### 1.1 Core Storage
- [ ] Implement `PostgresDataStore` adapter (implements `DataReader` + `DataWriter`)
- [ ] Set up SQLAlchemy async models + Alembic migrations for market data tables
- [ ] Implement `RedisCacheAdapter` (implements `CacheStore`)
- [ ] Write integration tests with Testcontainers (Postgres + Redis)

### 1.2 Market Data Ingestion
- [ ] Implement `PolygonMarketFeed` adapter (implements `ExternalDataSource`)
- [ ] Implement `FREDMacroSource` adapter for macro indicators
- [ ] Build data normalization pipeline in `application/`
- [ ] Write data quality validation logic
- [ ] End-to-end test: ingest → store → query via API

### 1.3 Event Publishing
- [ ] Implement `KafkaPublisher` adapter
- [ ] Publish `data.ingested` events on successful ingestion
- [ ] Consumer skeleton for downstream services

### 1.4 API Hardening
- [ ] Add auth middleware (JWT)
- [ ] Add rate limiting
- [ ] Add OpenAPI spec generation
- [ ] Add structured logging (structlog)

---

## Phase 2: Deterministic Engines (Layer 2)
> **Goal**: Core financial math engines operational and callable.

### 2.1 Rust — Portfolio Engine
- [ ] Implement `MeanVarianceOptimizer` (implements `AllocationStrategy`)
- [ ] Implement `BlackLittermanOptimizer` (implements `AllocationStrategy`)
- [ ] Implement portfolio rebalancing logic
- [ ] Unit tests with known analytical solutions

### 2.2 Rust — Risk Engine
- [ ] Implement `HistoricalVaR` (implements `RiskMeasure`)
- [ ] Implement `ConditionalVaR` (implements `RiskMeasure`)
- [ ] Implement stress testing scenarios
- [ ] Unit tests with known distributions

### 2.3 Rust — Monte Carlo Engine
- [ ] Implement `GBMSampler` (implements `PathSampler`)
- [ ] Implement `JumpDiffusionSampler`
- [ ] Scenario aggregation and confidence bands
- [ ] Benchmark tests (perf regression)

### 2.4 Rust — DCF & Fiscal
- [ ] Implement DCF valuation model
- [ ] Implement WACC calculator
- [ ] Implement sovereign debt stress testing
- [ ] Currency stability scoring

### 2.5 Rust — Graph Engine
- [ ] Implement generic graph data structure
- [ ] Financial contagion propagation
- [ ] Supply chain dependency modeling

### 2.6 Rust → Python Bridge (FFI)
- [ ] Expose portfolio optimizer via PyO3
- [ ] Expose risk engine via PyO3
- [ ] Expose Monte Carlo via PyO3
- [ ] Python integration tests calling Rust engines

### 2.7 Java — Enterprise APIs
- [ ] Spring Boot app with health endpoint
- [ ] Tax simulation domain service
- [ ] Capital efficiency scoring service
- [ ] REST controllers + global exception handler
- [ ] Flyway migrations
- [ ] JUnit 5 + Testcontainers tests

---

## Phase 3: ML / DL Stack (Layer 3)
> **Goal**: Trained models for regime detection, anomaly detection, and forecasting.

### 3.1 Statistical Models
- [ ] Implement ARIMA adapter (implements `Predictor`)
- [ ] Implement GARCH adapter for volatility modeling
- [ ] Implement VAR model
- [ ] PCA for factor decomposition

### 3.2 Classical ML
- [ ] XGBoost adapter (implements `Predictor`)
- [ ] Random Forest adapter
- [ ] Isolation Forest adapter (implements `AnomalyDetector`)
- [ ] Hidden Markov Model adapter (implements `RegimeClassifier`)

### 3.3 Deep Learning
- [ ] LSTM for sequential forecasting (implements `Predictor`)
- [ ] Transformer for time-series
- [ ] Autoencoder for anomaly detection (implements `AnomalyDetector`)
- [ ] GAN for stress path simulation
- [ ] GNN for network analysis

### 3.4 Training Pipeline
- [ ] Feature engineering from data-fabric
- [ ] Train/val/test split with time-series awareness
- [ ] Hyperparameter tuning
- [ ] Model evaluation + calibration scoring
- [ ] MLflow model registry integration

### 3.5 Inference API
- [ ] FastAPI prediction endpoints
- [ ] Model versioning in requests
- [ ] Batch prediction support
- [ ] Latency monitoring

---

## Phase 4: NLP & LLM Stack (Layer 4)
> **Goal**: Financial text understanding — sentiment, entity extraction, RAG.

### 4.1 Sentiment Analysis
- [ ] FinBERT adapter (implements `SentimentScorer`)
- [ ] Social media sentiment adapter
- [ ] Batch scoring API

### 4.2 Entity Extraction
- [ ] Earnings call parsing adapter (implements `EntityExtractor`)
- [ ] Policy speech analysis adapter
- [ ] spaCy NER adapter
- [ ] Company/person/event extraction

### 4.3 Embeddings & RAG
- [ ] Sentence transformer adapter (implements `TextEmbedder`)
- [ ] OpenAI embeddings adapter (alternative `TextEmbedder`)
- [ ] pgvector retriever adapter (implements `DocumentRetriever`)
- [ ] Document indexing pipeline
- [ ] RAG query pipeline

### 4.4 Detection
- [ ] Narrative shift detection
- [ ] Risk language detection
- [ ] Topic modeling

---

## Phase 5: Agent Orchestrator (Layer 5)
> **Goal**: LLM agent that decomposes queries, calls tools, and generates memos.

### 5.1 LLM Integration
- [ ] OpenAI adapter (implements `LLMProvider`)
- [ ] Anthropic adapter (implements `LLMProvider`)
- [ ] Local/Ollama adapter (implements `LLMProvider`)
- [ ] Structured output with Pydantic schemas

### 5.2 Tool System
- [ ] Tool registry with discovery
- [ ] Implement all 9 tool adapters calling downstream services
- [ ] Tool input/output validation
- [ ] Error handling and retry logic

### 5.3 Agent Core
- [ ] Task decomposition (planner)
- [ ] Multi-step execution with state tracking
- [ ] Confidence scoring across tool outputs
- [ ] Structured memo generation

### 5.4 Memory
- [ ] Conversation memory (short-term)
- [ ] RAG-based knowledge memory (long-term)
- [ ] Context window management

### 5.5 API Gateway
- [ ] Unified API gateway routing
- [ ] WebSocket support for streaming responses
- [ ] Session management
- [ ] Rate limiting per user

---

## Phase 6: Frontend (Dashboard)
> **Goal**: Next.js dashboard with financial visualizations.

### 6.1 Project Setup
- [ ] Initialize Next.js 14+ with App Router
- [ ] Configure TypeScript strict mode
- [ ] Set up design system / component library
- [ ] Configure authentication (NextAuth or similar)

### 6.2 Core Pages
- [ ] Dashboard overview with world state
- [ ] Macro analysis view (`/dashboard/macro`)
- [ ] Portfolio analysis view (`/dashboard/portfolio`)
- [ ] Company deep-dive (`/dashboard/company/[ticker]`)
- [ ] Policy simulation view (`/dashboard/policy`)
- [ ] Geopolitics view (`/dashboard/geopolitics`)

### 6.3 Data Visualization
- [ ] Real-time chart components (candlestick, line, area)
- [ ] Risk heatmaps
- [ ] Scenario tree visualization
- [ ] Portfolio allocation pie/donut charts
- [ ] World map for geopolitical risk

### 6.4 Agent Interface
- [ ] Chat interface for agent queries
- [ ] Streaming response display
- [ ] Structured memo rendering
- [ ] Confidence score visualization

---

## Phase 7: Smart Contracts (Optional)
> **Goal**: On-chain portfolio reporting and tokenized strategies.

- [ ] `IStratosVault.sol` interface
- [ ] Portfolio reporting contract
- [ ] Foundry test suite
- [ ] Deployment scripts

---

## Phase 8: Production Hardening
> **Goal**: Production-ready deployment with observability.

### 8.1 Security
- [ ] OWASP Top 10 audit
- [ ] Secrets management (Vault or AWS Secrets Manager)
- [ ] Input validation on all endpoints
- [ ] Rate limiting and DDoS protection

### 8.2 Observability
- [ ] Structured logging across all services
- [ ] Distributed tracing (OpenTelemetry)
- [ ] Metrics (Prometheus + Grafana dashboards)
- [ ] Alerting rules

### 8.3 CI/CD
- [ ] Automated test pipeline on PR
- [ ] Docker image building and registry push
- [ ] Staging deployment pipeline
- [ ] Production deployment with canary/blue-green

### 8.4 Infrastructure
- [ ] Terraform for cloud provisioning
- [ ] Kubernetes manifests (Kustomize overlays)
- [ ] Helm charts for service deployment
- [ ] Database backup and disaster recovery

---

## Priority Execution Order

```
Phase 0  ──→  Phase 1  ──→  Phase 2  ──→  Phase 3
(Foundation)  (Data)       (Engines)     (ML)
                              ↓
Phase 6  ←──  Phase 5  ←──  Phase 4
(Frontend)   (Agent)       (NLP)
                              ↓
              Phase 7  ──→  Phase 8
             (Contracts)   (Production)
```

### Recommended Sprint Mapping

| Sprint | Phase | Duration | Deliverable |
|--------|-------|----------|-------------|
| Sprint 1 | Phase 0 | 1 week | Repo + CI + empty shells compile |
| Sprint 2 | Phase 1 | 2 weeks | Market data flowing into TimescaleDB |
| Sprint 3-4 | Phase 2 | 3 weeks | Portfolio + Risk + MC engines operational |
| Sprint 5-6 | Phase 3 | 3 weeks | Regime detection + anomaly models trained |
| Sprint 7 | Phase 4 | 2 weeks | Sentiment + RAG pipeline working |
| Sprint 8-9 | Phase 5 | 2 weeks | Agent answering multi-tool queries |
| Sprint 10-11 | Phase 6 | 3 weeks | Dashboard with live data |
| Sprint 12 | Phase 7-8 | 2 weeks | Contracts + production hardening |

**Total estimated**: ~18 weeks (4.5 months) to production MVP.
