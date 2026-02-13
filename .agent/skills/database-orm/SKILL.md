---
name: database-orm
description: Database and ORM standards — PostgreSQL, MongoDB, Redis, Prisma, SQLAlchemy, TypeORM, Hibernate, SQLx, indexing, partitioning, migrations, and schema design
---

# Database & ORM Standards

## Schema Design Principles

1. **Normalize to 3NF minimum** for OLTP workloads.
2. **Denormalize with justification** for read-heavy analytics.
3. **Index all foreign keys** and frequently-queried columns.
4. **Use constraints** (CHECK, UNIQUE, NOT NULL) for data integrity.
5. **Always use migrations** — never manual DDL in production.

---

## PostgreSQL (15+)

### Naming Conventions
| Object | Convention | Example |
|---|---|---|
| Tables | `plural_snake_case` | `users`, `order_items` |
| Columns | `snake_case` | `created_at`, `user_id` |
| Primary keys | `id` | `id BIGINT` |
| Foreign keys | `{table}_id` | `user_id`, `order_id` |
| Indexes | `idx_{table}_{cols}` | `idx_users_email` |

### Table Template
```sql
CREATE TABLE users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    uuid UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_metadata ON users USING gin(metadata);
```

### Advanced Features
- **Partitioning**: Range on time columns for large tables.
- **JSONB**: For flexible metadata. Use GIN indexes.
- **Full-text search**: `tsvector` + GIN index.
- **Window functions**: `ROW_NUMBER()`, `RANK()`, `LAG()`, `LEAD()`.
- **CTEs**: For readable complex queries (`WITH ... AS`).
- **Materialized views**: For expensive aggregations (refresh periodically).

### Query Optimization
- Always `EXPLAIN ANALYZE` before optimizing.
- Use `LIMIT` + cursor-based pagination (not `OFFSET`).
- Prefer `EXISTS` over `IN` for subqueries.
- Use partial indexes for filtered queries.

---

## MongoDB (7+)

### Schema Design
- **Embed** for 1-to-few relationships (addresses in user doc).
- **Reference** for 1-to-many or many-to-many (orders → user_id).
- **Denormalize** read-heavy data.

### Indexes
```javascript
db.users.createIndex({ email: 1 }, { unique: true });
db.orders.createIndex({ userId: 1, createdAt: -1 });
db.sessions.createIndex({ createdAt: 1 }, { expireAfterSeconds: 86400 }); // TTL
db.articles.createIndex({ content: "text" }); // Full-text
```

### Aggregation Pipeline
```javascript
db.orders.aggregate([
  { $match: { status: "completed", createdAt: { $gte: ISODate("2024-01-01") } } },
  { $lookup: { from: "users", localField: "userId", foreignField: "_id", as: "user" } },
  { $unwind: "$user" },
  { $group: { _id: "$user.email", total: { $sum: "$total" }, count: { $sum: 1 } } },
  { $sort: { total: -1 } },
  { $limit: 10 },
]);
```

---

## Redis (7+)

### Use Cases & Patterns

| Use Case | Data Structure | Pattern |
|---|---|---|
| Caching | Strings | GET/SET with TTL |
| Sessions | Hashes | HSET/HGETALL |
| Rate limiting | Strings | INCR + EXPIRE |
| Leaderboards | Sorted Sets | ZADD/ZREVRANGE |
| Queues | Lists | LPUSH/BRPOP |
| Pub/Sub | Channels | PUBLISH/SUBSCRIBE |
| Distributed locks | Strings | SET NX PX |

### Cache-Aside Pattern
```python
value = await redis.get(cache_key)
if value is None:
    value = await db.query(...)
    await redis.setex(cache_key, 3600, serialize(value))
return deserialize(value)
```

---

## ORM: Prisma (TypeScript)

```prisma
// schema.prisma
model User {
  id        Int      @id @default(autoincrement())
  email     String   @unique
  name      String
  orders    Order[]
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  @@index([email])
}

model Order {
  id     Int         @id @default(autoincrement())
  userId Int
  total  Decimal     @db.Decimal(10, 2)
  status OrderStatus
  user   User        @relation(fields: [userId], references: [id])
  @@index([userId])
}

enum OrderStatus { PENDING COMPLETED CANCELLED }
```

### Queries
```typescript
// Include relations
const user = await prisma.user.findUnique({
  where: { id: 1 },
  include: { orders: { orderBy: { createdAt: 'desc' }, take: 10 } },
});

// Transaction
await prisma.$transaction(async (tx) => {
  await tx.user.update({ where: { id: 1 }, data: { balance: { decrement: 100 } } });
  await tx.order.create({ data: { userId: 1, total: 100, status: 'PENDING' } });
});
```

---

## ORM: SQLAlchemy 2.0 (Python)

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    orders: Mapped[list["Order"]] = relationship(back_populates="user", cascade="all, delete-orphan")

# Async query
async with AsyncSession(engine) as session:
    stmt = select(User).options(joinedload(User.orders)).where(User.id == 1)
    user = (await session.execute(stmt)).scalar_one()
```

---

## ORM: Hibernate / Spring Data JPA (Java)

```java
@Entity
@Table(name = "users", indexes = @Index(name = "idx_email", columnList = "email", unique = true))
public class User {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String email;

    @OneToMany(mappedBy = "user", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<Order> orders = new ArrayList<>();
}

// Repository
public interface UserRepository extends JpaRepository<User, Long> {
    Optional<User> findByEmail(String email);
    @Query("SELECT u FROM User u WHERE u.active = true AND u.createdAt >= :since")
    List<User> findActiveUsersSince(@Param("since") Instant since);
}
```

---

## ORM: SQLx (Rust)

```rust
#[derive(sqlx::FromRow)]
struct User { id: i64, name: String, email: String }

let user = sqlx::query_as!(User,
    "SELECT id, name, email FROM users WHERE id = $1", user_id
).fetch_one(&pool).await?;
```

---

## Migration Rules

1. **Versioned**: Use sequential numbering (`V001__create_users.sql`).
2. **Forward-only**: Never modify existing migrations.
3. **Reversible**: Provide `DOWN` migration where possible.
4. **Atomic**: Each migration is one logical change.
5. **Tools**: Flyway (Java), Alembic (Python), Prisma Migrate (TS), sqlx-migrate (Rust).

---

## Vector Databases (AI/ML)

| Database | Notes |
|---|---|
| pgvector | PostgreSQL extension — keep infra simple |
| Chroma | Lightweight, embedded |
| Pinecone | Managed, serverless |
| Weaviate | Multi-modal |
| Qdrant | Rust-based, fast |
| Milvus | Distributed, scalable |
