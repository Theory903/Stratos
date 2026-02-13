---
name: rust-standards
description: Rust 2021 edition standards — ownership, error handling, async with tokio, testing, Cargo workspace, and performance optimization
---

# Rust Standards

## Version & Tooling
- **Edition**: 2021 | **MSRV**: 1.75+
- **Linter**: `clippy` (pedantic) | **Formatter**: `rustfmt`

---

## Project Structure

### Binary
```
src/
├── main.rs
├── lib.rs
├── config.rs
├── error.rs
└── modules/
tests/
benches/
examples/
```

### Workspace
```toml
[workspace]
members = ["crates/*"]
resolver = "2"

[workspace.dependencies]
serde = { version = "1.0", features = ["derive"] }
tokio = { version = "1.0", features = ["full"] }
tracing = "0.1"
anyhow = "1.0"
thiserror = "1.0"
```

### Release Profile
```toml
[profile.release]
opt-level = 3
lto = true
codegen-units = 1
strip = true
panic = "abort"
```

---

## Naming

| Construct | Convention | Example |
|---|---|---|
| Crates/Modules | `snake_case` | `stratos_engine` |
| Types/Traits | `PascalCase` | `PortfolioEngine` |
| Functions | `snake_case` | `calculate_risk()` |
| Constants | `SCREAMING_SNAKE_CASE` | `MAX_PORTFOLIO_SIZE` |
| Macros | `snake_case!` | `debug_log!` |

---

## Ownership & Borrowing

1. **Prefer references over clones.**
2. **`&str` in parameters, `String` for returns that create data.**
3. **Use `Cow<'_, str>`** for functions that may or may not allocate.
4. **Interior mutability** (`RefCell`, `Mutex`) only when needed.

```rust
// Builder pattern
#[derive(Default)]
struct ConfigBuilder { host: Option<String>, port: Option<u16> }

impl ConfigBuilder {
    fn host(mut self, host: impl Into<String>) -> Self {
        self.host = Some(host.into()); self
    }
    fn port(mut self, port: u16) -> Self { self.port = Some(port); self }
    fn build(self) -> Result<Config> {
        Ok(Config {
            host: self.host.ok_or(ConfigError::MissingField("host"))?,
            port: self.port.unwrap_or(8080),
        })
    }
}
```

---

## Error Handling

### Library: `thiserror`
```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum EngineError {
    #[error("not found: {id}")]
    NotFound { id: String },
    #[error("insufficient balance: need {required}, have {available}")]
    InsufficientBalance { required: f64, available: f64 },
    #[error("database error")]
    Database(#[from] sqlx::Error),
    #[error("invalid config: {0}")]
    Config(String),
}
pub type Result<T> = std::result::Result<T, EngineError>;
```

### Application: `anyhow`
```rust
use anyhow::{Context, Result};
fn load_config(path: &str) -> Result<Config> {
    let content = std::fs::read_to_string(path).context("failed to read config")?;
    let config: Config = toml::from_str(&content).context("failed to parse config")?;
    Ok(config)
}
```

### Rules
- **Never `unwrap()` in production** — use `?` or `expect("reason")`.
- **`expect()` for invariants only** (programmer errors).
- **Add context** via `anyhow::Context`.

---

## Async (Tokio)

```rust
#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::init();
    let app = build_app().await?;
    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await?;
    axum::serve(listener, app).await?;
    Ok(())
}
```

### Concurrency
```rust
// Parallel
let (users, orders) = tokio::join!(fetch_users(&db), fetch_orders(&db));

// Timeout
tokio::select! {
    result = operation() => handle(result),
    _ = tokio::time::sleep(Duration::from_secs(30)) => Err(EngineError::Timeout),
}

// Structured concurrency
let mut set = tokio::task::JoinSet::new();
for url in urls { set.spawn(fetch_url(url)); }
while let Some(result) = set.join_next().await { process(result??); }
```

**Rules**: No `std::thread::sleep()` in async. Use `spawn_blocking` for CPU-bound. Limit concurrency with `Semaphore`.

---

## Testing

### Unit (in-file `#[cfg(test)]`)
```rust
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn test_risk_score_valid() {
        let p = Portfolio { assets: vec![Asset::new("AAPL", 0.5)] };
        assert!(calculate_risk(&p) > 0.0);
    }
    #[test]
    #[should_panic(expected = "empty portfolio")]
    fn test_risk_empty() { calculate_risk(&Portfolio { assets: vec![] }); }
    #[tokio::test]
    async fn test_async_fetch() { assert!(fetch("key").await.is_ok()); }
}
```

### Property Testing (proptest)
```rust
proptest! {
    #[test]
    fn roundtrip(input in ".*") {
        assert_eq!(input, decode(&encode(&input)).unwrap());
    }
}
```

---

## Documentation
```rust
/// Calculates portfolio risk using variance-covariance method.
///
/// # Arguments
/// * `weights` - Asset weights (must sum to 1.0)
/// * `cov_matrix` - Covariance matrix
///
/// # Errors
/// Returns [`EngineError::InvalidInput`] if dimensions mismatch.
///
/// # Examples
/// ```
/// let risk = calculate_portfolio_risk(&[0.6, 0.4], &cov).unwrap();
/// ```
pub fn calculate_portfolio_risk(weights: &[f64], cov_matrix: &[Vec<f64>]) -> Result<f64> { ... }
```

---

## Performance
1. **Iterators** — lazy, zero-cost. 2. **Avoid allocations** in hot paths.
3. **`#[inline]`** for small hot functions. 4. **Profile first**: `cargo flamegraph`, `criterion`.
5. **SIMD** for numerical code. 6. **Zero-copy**: `nom`, `winnow`.

---

## Key Crates

| Domain | Crate | Notes |
|---|---|---|
| Web | axum | Tower-based, async |
| Serialization | serde | Derive macros |
| Database | sqlx | Compile-time SQL verification |
| ORM | diesel | Type-safe queries |
| Async | tokio | Full runtime |
| Errors | thiserror + anyhow | Library + app |
| CLI | clap | Derive-based |
| Logging | tracing | Structured, async-aware |
| HTTP | reqwest | Async, TLS |
| Math | nalgebra, ndarray | Linear algebra |
| Testing | proptest, rstest | Property + parameterized |
