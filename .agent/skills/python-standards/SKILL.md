---
name: python-standards
description: Python 3.12+ language standards — style, typing, testing, async, project structure, and ecosystem libraries
---

# Python Standards

## Version & Runtime
- **Python**: 3.12+ (prefer latest stable)
- **Package manager**: `uv` (preferred) or `poetry`
- **Virtual environments**: Always. Never install globally.

---

## Project Structure (src layout)

```
project_root/
├── src/
│   └── package_name/
│       ├── __init__.py
│       ├── py.typed              # PEP 561 marker
│       ├── domain/               # Business entities, value objects
│       ├── application/          # Use cases, services
│       ├── infrastructure/       # DB, APIs, messaging adapters
│       └── presentation/         # CLI, REST, GraphQL endpoints
├── tests/
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/
├── pyproject.toml
├── README.md
├── .env.example
└── .python-version
```

---

## Code Style & Linting

### Formatter: `ruff format` (or `black`)
```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "F",    # pyflakes
    "I",    # isort
    "N",    # pep8-naming
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "S",    # flake8-bandit (security)
    "SIM",  # flake8-simplify
    "TCH",  # type-checking imports
    "RUF",  # ruff-specific rules
    "PTH",  # pathlib preference
    "ERA",  # eradicate commented code
]
ignore = ["E501"]  # line length handled by formatter

[tool.ruff.lint.isort]
known-first-party = ["package_name"]
```

### Type Checker: `mypy` (strict mode)
```toml
[tool.mypy]
python_version = "3.12"
strict = true
disallow_untyped_defs = true
disallow_any_unimported = true
warn_return_any = true
warn_unused_ignores = true
no_implicit_optional = true
check_untyped_defs = true
```

---

## Naming Conventions

| Construct | Convention | Example |
|---|---|---|
| Modules | `snake_case` | `user_service.py` |
| Classes | `PascalCase` | `UserService` |
| Functions/Methods | `snake_case` | `get_user_by_id()` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT` |
| Private | `_leading_underscore` | `_internal_helper()` |
| Type variables | `PascalCase` or single letter | `T`, `KT`, `VT` |
| Exceptions | `PascalCase` + `Error` suffix | `ValidationError` |

---

## Type Hints (Mandatory)

### Required For
- All function signatures (parameters + return type).
- All class attributes.
- Complex local variables where type isn't obvious.

### Modern Syntax (3.10+)
```python
# Use | instead of Union
def find(key: str) -> User | None: ...

# Use built-in generics
def process(items: list[dict[str, int]]) -> tuple[str, ...]: ...

# Use Protocol for structural typing (duck typing)
from typing import Protocol

class Readable(Protocol):
    def read(self, n: int = -1) -> bytes: ...

def consume(source: Readable) -> bytes:
    return source.read()

# Use TypeVar for generics
from typing import TypeVar, Generic

T = TypeVar("T")

class Repository(Generic[T]):
    def get(self, id: int) -> T | None: ...
    def save(self, entity: T) -> T: ...

# Use Literal for constrained values
from typing import Literal

def set_mode(mode: Literal["read", "write", "append"]) -> None: ...

# Use TypeAlias for complex types
type UserMap = dict[str, list[User]]
```

---

## Docstrings (Google Style)

```python
def calculate_discount(
    price: Decimal,
    rate: Decimal,
    *,
    minimum: Decimal = Decimal("0.01"),
) -> Decimal:
    """Calculate discounted price with minimum floor.

    Applies a percentage discount to the original price, ensuring the
    result never falls below the specified minimum.

    Args:
        price: Original price in USD. Must be positive.
        rate: Discount rate as decimal (0.0 to 1.0).
        minimum: Minimum allowed price after discount.

    Returns:
        Discounted price rounded to 2 decimal places.

    Raises:
        ValueError: If rate is not between 0 and 1.
        ValueError: If price is negative.

    Examples:
        >>> calculate_discount(Decimal("100.00"), Decimal("0.20"))
        Decimal('80.00')

        >>> calculate_discount(Decimal("1.00"), Decimal("0.99"))
        Decimal('0.01')
    """
```

---

## Error Handling

### Rules
1. **Never bare `except:`** — always catch specific exceptions.
2. **Re-raise with context** using `from`:
   ```python
   try:
       result = db.query(sql)
   except DatabaseError as e:
       raise DataAccessError(f"Failed to query users: {sql}") from e
   ```
3. **Use context managers** for resource cleanup:
   ```python
   from contextlib import contextmanager

   @contextmanager
   def managed_connection(url: str):
       conn = create_connection(url)
       try:
           yield conn
       finally:
           conn.close()
   ```
4. **Custom exception hierarchy**:
   ```python
   class AppError(Exception):
       """Base exception for the application."""
       def __init__(self, message: str, code: str) -> None:
           super().__init__(message)
           self.code = code

   class NotFoundError(AppError):
       def __init__(self, resource: str, id: str) -> None:
           super().__init__(f"{resource} not found: {id}", "NOT_FOUND")

   class ValidationError(AppError):
       def __init__(self, errors: dict[str, str]) -> None:
           super().__init__("Validation failed", "VALIDATION_ERROR")
           self.errors = errors
   ```

---

## Async Programming

### Runtime: `asyncio`
### HTTP client: `httpx` (async)
### DB: `asyncpg` (PostgreSQL), `motor` (MongoDB)

### Rules
- **Never block the event loop** — no `time.sleep()`, `requests.get()` in async code.
- **Use async context managers** for connections.
- **Handle `CancelledError`** for graceful shutdown.
- **Use `asyncio.TaskGroup`** (3.11+) for structured concurrency:
  ```python
  async def fetch_all(urls: list[str]) -> list[Response]:
      async with asyncio.TaskGroup() as tg:
          tasks = [tg.create_task(fetch(url)) for url in urls]
      return [t.result() for t in tasks]
  ```

---

## Testing with pytest

### Configuration
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_functions = "test_*"
addopts = [
    "--strict-markers",
    "--cov=src",
    "--cov-report=term-missing",
    "--cov-fail-under=80",
    "-x",               # Stop on first failure
    "--tb=short",
]
markers = [
    "slow: marks tests as slow",
    "integration: requires external services",
]
```

### Fixtures
```python
import pytest
from unittest.mock import AsyncMock, Mock

@pytest.fixture
def user_repo() -> Mock:
    repo = Mock(spec=UserRepository)
    repo.find_by_email = AsyncMock(return_value=None)
    repo.save = AsyncMock(side_effect=lambda u: u)
    return repo

@pytest.fixture
def user_service(user_repo: Mock) -> UserService:
    return UserService(repository=user_repo)
```

### Parameterized Tests
```python
@pytest.mark.parametrize("email,valid", [
    ("user@example.com", True),
    ("invalid", False),
    ("", False),
    ("a@b.c", True),
])
def test_email_validation(email: str, valid: bool) -> None:
    assert is_valid_email(email) == valid
```

### Async Tests
```python
@pytest.mark.asyncio
async def test_create_user(user_service: UserService, user_repo: Mock) -> None:
    request = CreateUserRequest(name="John", email="john@example.com")
    result = await user_service.create(request)

    assert result.name == "John"
    user_repo.save.assert_awaited_once()
```

---

## Dependency Management

### pyproject.toml (PEP 621)
```toml
[project]
name = "stratos-ml"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.110",
    "httpx>=0.27",
    "pydantic>=2.6",
    "sqlalchemy[asyncio]>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "mypy>=1.9",
    "ruff>=0.3",
]
```

### Version Pinning
- **Libraries**: Use `>=` compatible ranges (`httpx>=0.27`).
- **Applications**: Pin exact in lockfile (`uv.lock` / `poetry.lock`). Commit lockfiles.

### Security Scanning
- `pip-audit` — check for known vulnerabilities.
- `bandit` — static security analysis.
- Run both in CI on every build.

---

## Performance Guidelines

1. **Profile before optimizing**: Use `cProfile`, `py-spy`, or `scalene`.
2. **Use built-in functions**: `sum()`, `min()`, `max()`, `sorted()`, `any()`, `all()`.
3. **Generators for large data**: Avoid materializing full lists.
4. **`__slots__`** on data-heavy classes:
   ```python
   from dataclasses import dataclass

   @dataclass(slots=True, frozen=True)
   class Point:
       x: float
       y: float
   ```
5. **List comprehensions** over `map()`/`filter()` for simple transforms.
6. **`functools.lru_cache`** for expensive pure computations.
7. **Avoid global imports of heavy libraries** — lazy import in function scope if startup-critical.

---

## Key Libraries Ecosystem

| Domain | Library | Notes |
|---|---|---|
| Web API | FastAPI | Async, Pydantic, auto-docs |
| ORM | SQLAlchemy 2.0 | Async, type-safe queries |
| Validation | Pydantic v2 | Fast, JSON Schema |
| HTTP client | httpx | Async, HTTP/2 |
| Task queue | Celery / ARQ | Background jobs |
| CLI | Typer / Click | Type-safe CLIs |
| Config | pydantic-settings | Env-based config |
| Logging | structlog | Structured JSON logs |
| Data | pandas / polars | DataFrames |
| ML | scikit-learn, PyTorch | ML pipelines |
| LLM | langchain, llama-index | Agent frameworks |
| Testing | pytest, hypothesis | Property testing |
