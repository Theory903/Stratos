---
name: typescript-standards
description: TypeScript 5.0+ language standards — strict mode, type system patterns, error handling, async, testing with vitest, and project configuration
---

# TypeScript Standards

## Version & Configuration
- **TypeScript**: 5.0+ (latest stable)
- **Runtime**: Node.js 20+ LTS or Bun
- **Module system**: ESM (`"type": "module"` in package.json)

---

## tsconfig.json (Strict)

```jsonc
{
  "compilerOptions": {
    // Target
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],

    // Strict Type Checking (ALL enabled)
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "strictBindCallApply": true,
    "strictPropertyInitialization": true,
    "noImplicitThis": true,
    "alwaysStrict": true,

    // Additional Safety
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,

    // Interop
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "isolatedModules": true,

    // Output
    "noEmit": true,
    "jsx": "react-jsx",

    // Path Aliases
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

---

## Code Style

### Formatter: Prettier
```json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2,
  "arrowParens": "always"
}
```

### Linter: ESLint (flat config)
```js
// eslint.config.js
import tseslint from 'typescript-eslint';

export default tseslint.config(
  ...tseslint.configs.strictTypeChecked,
  {
    rules: {
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/prefer-const': 'error',
      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/no-misused-promises': 'error',
      '@typescript-eslint/consistent-type-imports': 'error',
      'no-console': 'warn',
    },
  }
);
```

---

## Naming Conventions

| Construct | Convention | Example |
|---|---|---|
| Files | `kebab-case.ts` | `user-service.ts` |
| Classes | `PascalCase` | `UserService` |
| Interfaces | `PascalCase` (no `I` prefix) | `UserRepository` |
| Types | `PascalCase` | `CreateUserRequest` |
| Functions | `camelCase` | `getUserById()` |
| Variables | `camelCase` | `maxRetryCount` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_CONNECTIONS` |
| Enums | `PascalCase` (values too) | `UserRole.Admin` |
| Generics | Single letter or descriptive | `T`, `TEntity` |

---

## Type System — Advanced Patterns

### Branded/Opaque Types
```typescript
type UserId = string & { readonly __brand: 'UserId' };
type Email = string & { readonly __brand: 'Email' };

function createUserId(raw: string): UserId {
  if (!raw.trim()) throw new Error('Empty user ID');
  return raw as UserId;
}
```

### Discriminated Unions
```typescript
type Result<T, E = Error> =
  | { ok: true; data: T }
  | { ok: false; error: E };

function handleResult<T>(result: Result<T>): T {
  if (result.ok) {
    return result.data; // TypeScript narrows correctly
  }
  throw result.error;
}
```

### Template Literal Types
```typescript
type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE';
type Route = `/${string}`;
type Endpoint = `${HttpMethod} ${Route}`;
// "GET /users" ✓    "PATCH /users" ✗
```

### Utility Types (use liberally)
| Type | Purpose |
|---|---|
| `Partial<T>` | All properties optional |
| `Required<T>` | All properties required |
| `Readonly<T>` | All properties readonly |
| `Pick<T, K>` | Subset of properties |
| `Omit<T, K>` | Exclude properties |
| `Record<K, V>` | Key-value map |
| `ReturnType<F>` | Function return type |
| `Parameters<F>` | Function parameter types |
| `Awaited<T>` | Unwrap Promise type |
| `NonNullable<T>` | Exclude null/undefined |

### Const Assertions
```typescript
const ROLES = ['admin', 'user', 'viewer'] as const;
type Role = (typeof ROLES)[number]; // "admin" | "user" | "viewer"
```

### Zod Schema Validation (infer types from schemas)
```typescript
import { z } from 'zod';

const CreateUserSchema = z.object({
  name: z.string().min(2).max(100),
  email: z.string().email(),
  role: z.enum(['admin', 'user', 'viewer']),
});

type CreateUserRequest = z.infer<typeof CreateUserSchema>;
// { name: string; email: string; role: "admin" | "user" | "viewer" }
```

---

## Error Handling

### Custom Error Classes
```typescript
class AppError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly statusCode: number,
    public readonly details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'AppError';
  }
}

class NotFoundError extends AppError {
  constructor(resource: string, id: string) {
    super(`${resource} not found: ${id}`, 'NOT_FOUND', 404);
  }
}

class ValidationError extends AppError {
  constructor(errors: Record<string, string>) {
    super('Validation failed', 'VALIDATION_ERROR', 400, { errors });
  }
}
```

### Result Pattern (functional error handling)
```typescript
type Result<T, E = AppError> =
  | { success: true; data: T }
  | { success: false; error: E };

function ok<T>(data: T): Result<T, never> {
  return { success: true, data };
}

function err<E>(error: E): Result<never, E> {
  return { success: false, error };
}

// Usage
async function getUser(id: string): Promise<Result<User>> {
  const user = await db.users.findUnique({ where: { id } });
  if (!user) return err(new NotFoundError('User', id));
  return ok(user);
}
```

### Rules
- **Never throw strings** — always throw Error instances.
- **Never `catch` and ignore** — log or propagate.
- **Use `unknown` in catch** — TypeScript 4.4+ default:
  ```typescript
  try {
    await riskyOperation();
  } catch (error: unknown) {
    if (error instanceof AppError) {
      logger.warn(error.message, { code: error.code });
    } else {
      logger.error('Unexpected error', { error });
      throw error;
    }
  }
  ```

---

## Async Patterns

### Prefer async/await over raw Promises
```typescript
// ✅ Good
const user = await fetchUser(id);
const orders = await fetchOrders(user.id);

// ✅ Good — parallel execution
const [users, products, orders] = await Promise.all([
  fetchUsers(),
  fetchProducts(),
  fetchOrders(),
]);

// ✅ Good — settle all, don't fail fast
const results = await Promise.allSettled([
  fetchFromApi(),
  fetchFromCache(),
]);

for (const result of results) {
  if (result.status === 'fulfilled') {
    process(result.value);
  } else {
    logger.warn('Fetch failed', { reason: result.reason });
  }
}
```

### Abort Controllers for Cancellation
```typescript
async function fetchWithTimeout(url: string, timeoutMs: number): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(url, { signal: controller.signal });
  } finally {
    clearTimeout(timeoutId);
  }
}
```

---

## Testing with Vitest

### Configuration
```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['src/**/*.test.ts', 'tests/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: ['node_modules/', 'dist/', '**/*.test.ts', '**/*.d.ts'],
      thresholds: { lines: 80, functions: 80, branches: 80, statements: 80 },
    },
  },
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
});
```

### Test Patterns
```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('UserService', () => {
  let service: UserService;
  let mockRepo: { findById: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    mockRepo = { findById: vi.fn() };
    service = new UserService(mockRepo as unknown as UserRepository);
  });

  it('should return user when found', async () => {
    // Arrange
    const expected = { id: '1', name: 'John', email: 'john@test.com' };
    mockRepo.findById.mockResolvedValue(expected);

    // Act
    const result = await service.getUser('1');

    // Assert
    expect(result).toEqual(expected);
    expect(mockRepo.findById).toHaveBeenCalledWith('1');
    expect(mockRepo.findById).toHaveBeenCalledTimes(1);
  });

  it('should throw NotFoundError when user missing', async () => {
    mockRepo.findById.mockResolvedValue(null);

    await expect(service.getUser('999')).rejects.toThrow(NotFoundError);
  });
});
```

### Parameterized Tests
```typescript
it.each([
  { input: 'user@example.com', expected: true },
  { input: 'invalid', expected: false },
  { input: '', expected: false },
])('validates email "$input" as $expected', ({ input, expected }) => {
  expect(isValidEmail(input)).toBe(expected);
});
```

---

## Project Structure

```
src/
├── index.ts                  # Entry point
├── config/
│   └── env.ts                # Environment config (Zod-validated)
├── types/
│   └── index.ts              # Shared type definitions
├── lib/
│   ├── errors.ts             # Error classes
│   ├── logger.ts             # Structured logger
│   └── utils.ts              # Pure utility functions
├── domain/
│   ├── user/
│   │   ├── user.entity.ts
│   │   ├── user.repository.ts   # Interface
│   │   └── user.service.ts
│   └── order/
│       └── ...
├── infrastructure/
│   ├── database/
│   │   ├── prisma.ts
│   │   └── user.repository.impl.ts
│   └── http/
│       └── api-client.ts
└── presentation/
    ├── routes/
    │   └── user.routes.ts
    └── middleware/
        ├── error-handler.ts
        └── auth.ts
```

---

## Key Libraries

| Domain | Library | Notes |
|---|---|---|
| Validation | zod | Schema-first, infer types |
| HTTP framework | fastify / express | See node-api-frameworks skill |
| ORM | prisma / drizzle | Type-safe queries |
| HTTP client | ofetch / ky / axios | Typed responses |
| Testing | vitest | Fast, ESM-native |
| Logging | pino | JSON structured logs |
| Config | @t3-oss/env-nextjs / zod | Validated env vars |
| Auth | lucia / next-auth | Session management |
| CLI | commander / citty | CLI tools |
| Date | date-fns / dayjs | Immutable date operations |
