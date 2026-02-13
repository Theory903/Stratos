---
name: testing-standards
description: Testing standards — testing pyramid, unit/integration/e2e patterns, mocking, property testing, coverage, and frameworks
---

# Testing Standards

## Testing Pyramid

| Level | % | Speed | Scope | Frameworks |
|---|---|---|---|---|
| Unit | 70% | <100ms | Function/class | pytest, vitest, JUnit, `#[test]` |
| Integration | 20% | <5s | Components, DB, APIs | Testcontainers, supertest |
| E2E | 10% | <30s | Full workflows | Playwright, Cypress |

---

## Test Structure (AAA Pattern)

Every test follows: **Arrange → Act → Assert**

```python
# Python
def test_create_order_calculates_total():
    # Arrange
    items = [OrderItem(price=Decimal("10.00"), qty=2), OrderItem(price=Decimal("5.00"), qty=1)]

    # Act
    order = Order.create(items)

    # Assert
    assert order.total == Decimal("25.00")
    assert order.item_count == 3
```

**Rules:**
- One test = one concept.
- No logic in assertions (no `if`, `for`, `while`).
- Tests must be independent and idempotent.
- Tests must be deterministic (no random, no system clock without mocking).

---

## Test Naming Conventions

Choose one and be consistent across the project:

```
# Option A
test_[method]_[scenario]_[expectedResult]
test_calculate_discount_with_expired_coupon_returns_zero

# Option B
should_[result]_when_[scenario]
should_return_404_when_user_not_found

# Option C (BDD)
given_[context]_when_[action]_then_[result]
given_empty_cart_when_checkout_then_throws_validation_error
```

---

## Mocking Best Practices

1. **Mock external dependencies** — DB, APIs, filesystem, clock.
2. **Never mock the system under test.**
3. **Verify interactions** — called once, called with args.
4. **Prefer fakes over mocks** for complex dependencies.
5. **Avoid deep mock chains** (mock.a.b.c.method) — sign of coupling.

```typescript
// TypeScript — vitest mocking
const mockRepo = {
  findById: vi.fn().mockResolvedValue({ id: '1', name: 'John' }),
  save: vi.fn().mockImplementation((user) => Promise.resolve(user)),
};
```

---

## Property-Based Testing

```python
# Python — hypothesis
from hypothesis import given, strategies as st

@given(st.lists(st.integers(), min_size=1))
def test_sort_preserves_length(lst):
    assert len(sorted(lst)) == len(lst)

@given(st.lists(st.integers(), min_size=1))
def test_sort_is_idempotent(lst):
    assert sorted(sorted(lst)) == sorted(lst)
```

```rust
// Rust — proptest
proptest! {
    #[test]
    fn roundtrip(s in "\\PC*") {
        assert_eq!(s, decode(&encode(&s)).unwrap());
    }
}
```

---

## Coverage Thresholds

| Scope | Minimum | Ideal |
|---|---|---|
| Overall | 80% | 90% |
| Critical paths (auth, payments) | 95% | 100% |
| New code | Must not decrease | — |
| Utility/helper code | 90% | 95% |

---

## E2E Testing (Playwright)

```typescript
import { test, expect } from '@playwright/test';

test('user can log in and see dashboard', async ({ page }) => {
  await page.goto('/login');
  await page.fill('[data-testid="email"]', 'user@test.com');
  await page.fill('[data-testid="password"]', 'password123');
  await page.click('[data-testid="submit"]');
  await expect(page).toHaveURL('/dashboard');
  await expect(page.locator('h1')).toContainText('Welcome');
});
```

---

## Integration Testing with Testcontainers

```python
# Python
import testcontainers.postgres

@pytest.fixture(scope="session")
def db():
    with PostgresContainer("postgres:16-alpine") as pg:
        engine = create_engine(pg.get_connection_url())
        Base.metadata.create_all(engine)
        yield engine
```

```java
// Java
@Testcontainers
@SpringBootTest
class IT {
    @Container
    static PostgreSQLContainer<?> pg = new PostgreSQLContainer<>("postgres:16-alpine");

    @DynamicPropertySource
    static void configure(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", pg::getJdbcUrl);
    }
}
```

---

## Anti-Patterns to Avoid

- ❌ Testing implementation details (private methods).
- ❌ Tests that depend on execution order.
- ❌ Sleeping (`time.sleep`) instead of polling/awaiting.
- ❌ Testing framework behavior (e.g., testing that FastAPI validates).
- ❌ Brittle snapshot tests on frequently-changing output.
- ❌ Ignoring flaky tests — fix or remove them.
