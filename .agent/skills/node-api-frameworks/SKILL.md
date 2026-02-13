---
name: node-api-frameworks
description: Node.js API framework standards — Express 4.x, Fastify 4.x, NestJS patterns, middleware, validation, error handling, and security
---

# Node API Frameworks

## Express (4.18+)

### Structure
```
src/
├── app.ts                # Express app setup
├── server.ts             # HTTP server start
├── routes/
│   └── users.route.ts
├── controllers/
│   └── users.controller.ts
├── services/
│   └── users.service.ts
├── middleware/
│   ├── error-handler.ts
│   ├── validate.ts
│   └── auth.ts
├── schemas/
│   └── users.schema.ts   # Zod schemas
└── types/
    └── index.ts
```

### Error Middleware
```typescript
import type { Request, Response, NextFunction } from 'express';

function errorHandler(err: unknown, _req: Request, res: Response, _next: NextFunction) {
  if (err instanceof AppError) {
    return res.status(err.statusCode).json({
      code: err.code, message: err.message, timestamp: new Date().toISOString(),
    });
  }
  console.error('Unexpected error:', err);
  res.status(500).json({ code: 'INTERNAL_ERROR', message: 'Something went wrong' });
}
```

### Async Wrapper
```typescript
const asyncHandler = (fn: (req: Request, res: Response, next: NextFunction) => Promise<void>) =>
  (req: Request, res: Response, next: NextFunction) => fn(req, res, next).catch(next);

router.get('/users/:id', asyncHandler(async (req, res) => {
  const user = await userService.getById(req.params.id);
  res.json(user);
}));
```

---

## Fastify (4.0+)

### Setup with TypeBox
```typescript
import Fastify from 'fastify';
import { Type as T, Static } from '@sinclair/typebox';

const app = Fastify({ logger: { level: 'info', transport: { target: 'pino-pretty' } } });

const UserSchema = T.Object({
  id: T.String({ format: 'uuid' }),
  name: T.String({ minLength: 2 }),
  email: T.String({ format: 'email' }),
});
type User = Static<typeof UserSchema>;

app.get('/users/:id', {
  schema: {
    params: T.Object({ id: T.String({ format: 'uuid' }) }),
    response: { 200: UserSchema },
  },
}, async (request, reply) => {
  const user = await userService.getById(request.params.id);
  return user;
});
```

**Fastify advantages**: Built-in validation, serialization, logging, lifecycle hooks.

---

## Security Middleware (Both)

```typescript
import helmet from 'helmet';
import cors from 'cors';
import rateLimit from 'express-rate-limit';

app.use(helmet());
app.use(cors({ origin: process.env.ALLOWED_ORIGINS?.split(','), credentials: true }));
app.use(rateLimit({ windowMs: 15 * 60 * 1000, max: 100 }));
```

---

## Key Libraries

| Library | Purpose |
|---|---|
| express / fastify | HTTP framework |
| zod / typebox | Validation |
| helmet | Security headers |
| cors | CORS configuration |
| express-rate-limit | Rate limiting |
| pino / winston | Logging |
| passport / jose | Authentication |
| swagger-jsdoc | API documentation |
| supertest | HTTP testing |
