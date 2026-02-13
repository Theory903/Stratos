---
name: nextjs-framework
description: Next.js 14+ App Router standards — Server Components, Server Actions, caching, metadata API, optimization, and rendering patterns
---

# Next.js Framework Standards

## Version & Setup
- **Next.js**: 14+ (App Router)
- **React**: 18+
- **TypeScript**: Required (see typescript-standards skill)

---

## Project Structure (App Router)
```
src/
├── app/
│   ├── layout.tsx            # Root layout (fonts, providers)
│   ├── page.tsx              # Home page
│   ├── loading.tsx           # Loading UI
│   ├── error.tsx             # Error boundary
│   ├── not-found.tsx         # 404 page
│   ├── (auth)/               # Route group (no URL segment)
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   ├── dashboard/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── [id]/page.tsx     # Dynamic route
│   └── api/
│       └── route.ts          # API route handler
├── components/
│   ├── ui/                   # Primitives (Button, Input)
│   └── features/             # Feature components
├── lib/
│   ├── actions.ts            # Server Actions
│   ├── db.ts                 # Database client
│   └── utils.ts
├── styles/
│   └── globals.css
└── types/
    └── index.ts
```

---

## Server vs Client Components

### Server Components (Default)
```tsx
// app/posts/page.tsx — Server Component (no "use client")
import { db } from '@/lib/db';

export default async function PostsPage() {
  const posts = await db.post.findMany({ orderBy: { createdAt: 'desc' } });

  return (
    <main>
      {posts.map((post) => (
        <article key={post.id}>
          <h2>{post.title}</h2>
          <p>{post.excerpt}</p>
        </article>
      ))}
    </main>
  );
}
```

### Client Components
Use `"use client"` ONLY when component needs:
- `useState`, `useEffect`, `useRef`
- Event handlers (`onClick`, `onChange`)
- Browser APIs (`window`, `localStorage`)
- Third-party client libraries

```tsx
'use client';
import { useState } from 'react';

export function SearchBar({ onSearch }: { onSearch: (q: string) => void }) {
  const [query, setQuery] = useState('');
  return (
    <input value={query} onChange={(e) => setQuery(e.target.value)}
           onKeyDown={(e) => e.key === 'Enter' && onSearch(query)} />
  );
}
```

**Rule: Keep client components as small as possible. Push state to leaf nodes.**

---

## Server Actions

```tsx
// lib/actions.ts
'use server';
import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { z } from 'zod';

const CreatePostSchema = z.object({
  title: z.string().min(3).max(200),
  content: z.string().min(10),
});

export async function createPost(formData: FormData) {
  const parsed = CreatePostSchema.safeParse({
    title: formData.get('title'),
    content: formData.get('content'),
  });

  if (!parsed.success) {
    return { errors: parsed.error.flatten().fieldErrors };
  }

  await db.post.create({ data: parsed.data });
  revalidatePath('/posts');
  redirect('/posts');
}
```

---

## Data Fetching & Caching

```tsx
// Opt out of caching for dynamic data
export const dynamic = 'force-dynamic';

// Or cache with revalidation
export const revalidate = 3600; // Revalidate every hour

// Per-request caching
async function getUser(id: string) {
  const res = await fetch(`${API_URL}/users/${id}`, {
    next: { revalidate: 60, tags: [`user-${id}`] },
  });
  if (!res.ok) throw new Error('Failed to fetch user');
  return res.json();
}

// Revalidate on demand
import { revalidateTag } from 'next/cache';
revalidateTag(`user-${id}`);
```

---

## Metadata & SEO

```tsx
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'STRATOS Dashboard',
  description: 'Strategic financial intelligence platform',
  openGraph: { title: 'STRATOS', type: 'website' },
};

// Dynamic metadata
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const post = await getPost(params.id);
  return { title: post.title, description: post.excerpt };
}
```

---

## Optimization

- **Images**: Use `next/image` with `width`/`height` or `fill`.
- **Fonts**: Use `next/font/google` (zero layout shift).
- **Dynamic imports**: `next/dynamic` for heavy client components.
- **Parallel routes**: Use `@slot` convention for parallel data loading.
- **Streaming**: Use `loading.tsx` and `Suspense` boundaries.

---

## Key Libraries

| Library | Purpose |
|---|---|
| next-auth / lucia | Authentication |
| zod | Schema validation |
| prisma / drizzle | Database ORM |
| tailwindcss | Utility-first CSS |
| @t3-oss/env-nextjs | Validated env variables |
| next-intl | Internationalization |
| next-themes | Dark/light mode |
