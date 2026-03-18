# Changelog

All notable changes to STRATOS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0-MVP] - 2024

### ✅ Added - V1 MVP Release

#### Data Fabric (Layer 1)
- Complete data ingestion pipeline with multi-source connectors
- PostgreSQL + TimescaleDB integration for time-series data
- FastAPI REST API for data queries and feature engineering
- Support for market feeds, macro databases, corporate filings, news APIs
- Market Intelligence module with real-time data providers (Alpha Vantage, Finnhub, CoinGecko, NewsAPI, Yahoo Finance)
- Research routes for sophisticated data analysis and backtesting
- Adaptive caching and optimization strategies

#### Deterministic Engines (Layer 2)
- **Rust Engine (8 crates)**:
  - Core financial primitives and data structures
  - Portfolio optimization engine with transaction costs and liquidity constraints
  - Risk engine with multi-factor models
  - DCF valuation model with scenario analysis
  - Monte Carlo simulator for tail risk analysis
  - Fiscal sustainability model for sovereign analysis
  - Graph propagation engine for shock propagation
  - FFI bindings for cross-language integration
  
- **GraphEngine**: Uncertainty-aware impact propagation with impact bands
- ADV-based liquidity constraint modeling
- Transaction cost and turnover penalty models (Linear/Quadratic)

#### ML/DL Stack (Layer 3)
- PyTorch-based model infrastructure
- ARIMA, GARCH, VAR models for time-series
- XGBoost, Random Forest for classification
- Isolation Forest for anomaly detection
- Hidden Markov Models for regime detection
- Configurable model registry and persistence

#### NLP & LLM Stack (Layer 4)
- FinBERT integration for financial sentiment analysis
- Sentence transformers for semantic embeddings
- RAG (Retrieval-Augmented Generation) memory store
- Spacy-based NER for entity extraction
- Topic modeling and narrative detection
- FastAPI routes for text analysis endpoints

#### Agent Orchestrator (Layer 5)
- **Finance Council**: Multi-agent consensus framework
  - Analysts for corporate and market analysis
  - Quant specialists for risk and portfolio analysis
  - Risk managers for constraint enforcement
  - Traders for execution recommendations
  - Supervisors for debate and resolution
  
- **Tool Ecosystem** (15+ specialized tools):
  - Portfolio allocation tools
  - Tax optimization engines
  - Market data tools (Alpha Vantage, Finnhub, CoinGecko)
  - Company research and news tools
  - Macro indicators and policy event tools
  - Social sentiment tools
  - Decision context and signal tools
  - Provider health monitoring
  
- **Langchain V3 Integration**:
  - Tool-calling orchestration
  - Structured output generation
  - Multi-turn conversation support
  - Context management and memory
  
- **V5 Runtime System**:
  - Graph-based workflow execution
  - State persistence and checkpointing
  - Signal-based decision making
  - Workspace management for multi-user scenarios
  - Approval gate workflows
  
- **Persistence Layer**: SQLite-based state management
- PolicyGuard for scalar risk limit enforcement

#### Frontend (Layer 6)
- Next.js 14 full-stack application with TypeScript
- **Dashboard Views**:
  - Agent workspace with real-time execution tracking
  - Portfolio management and allocation interface
  - Research explorer for backtesting and signal analysis
  - Studio for prompt engineering and tool testing
  - Settings for user preferences and API management
  
- **Dashboard Components**:
  - Approval gate interface for human-in-the-loop decisions
  - Financial metrics panels and key-value displays
  - Structured list visualization for complex outputs
  - Signal visualization and interpretation
  - Handoff context for human-AI collaboration
  
- **Command Palette**: Quick navigation and command execution
- Runtime flags for feature toggling
- Signals system for real-time updates
- Full authentication and user session management

#### Smart Contracts (Solidity)
- Framework setup with Foundry
- Contract testing infrastructure
- Deployment ready for institutional features

#### Infrastructure
- Docker Compose configuration for local development
- 7 Dockerfiles for all microservices
- GitHub Actions CI/CD pipeline
- Environment configuration management
- Database schema migrations and seed scripts

#### Documentation
- Comprehensive README with architecture overview
- API endpoint documentation
- Design principle documentation
- PRD with complete vision and requirements
- Architectural decision records

### 🔄 Changed
- Migrated Next.js frontend from Pages Router to App Router (Next.js 14)
- Refactored environment configuration system for multi-environment support
- Enhanced error handling and logging across all services
- Improved database connection pooling and optimization
- Updated dependency management across monorepo

### 🐛 Fixed
- Fixed import resolution issues in shared protocols
- Corrected database migration paths
- Resolved async/await patterns in FastAPI routes
- Fixed type safety issues in TypeScript components

### 🗑️ Removed
- Legacy HTML concept files
- Deprecated Pages Router components
- Old Keycloak realm configuration (planned for V2)

### 📊 Statistics
- **137 files changed** across all modules
- **23,000+ lines of code** added/modified
- **6 language polyglot** (Python, Rust, TypeScript, SQL, Solidity, YAML)
- **100+ API endpoints** implemented
- **15+ specialized tools** in agent ecosystem
- **8 Rust crates** for deterministic computation
- **Full test coverage** setup for all services

---

## [Unreleased] - V2 Roadmap

### Planned for V2
- Point-in-Time (PiT) snapshots with hindsight-bias protection
- Regime Stability Score with quantified certainty metrics
- Probability-weighted scenario joint distributions
- Multi-dimensional constraint system (sector concentration, correlation spikes)
- Automatic de-risking logic based on volatility/correlation triggers
- Capital Scaling Simulation ($10M vs $100M impact modeling)
- Calibration Dashboard (Probability vs Frequency tracking)
- Brier Score history tracking for model calibration
- STRATOS Crisis Certification Framework:
  - Stress Replay Harness (2008, 2020, 2022 survivor tests)
  - Adversarial noise injection on data feeds
  - Model drift detection system
  - Unoverrideable kill-switch for exposure reduction
- Institutional dashboard and reporting
- Advanced geopolitical simulation engines
- Enhanced fraud detection with adversarial robustness
- Public policy advisory module
- Sovereign crisis early warning system