import "server-only"

import { randomBytes, randomUUID, scryptSync, timingSafeEqual } from "node:crypto"

import { Pool } from "pg"

import { AppSession, OnboardingDraft, WorkspaceState } from "@/lib/app-state"

type UserRow = {
  id: string
  email: string
  name: string
  password_hash: string
  created_at: Date
}

type SessionRow = {
  id: string
  user_id: string
  expires_at: Date
  created_at: Date
  email: string
  name: string
}

type UserStateRow = {
  workspace_json: WorkspaceState
  draft_json: OnboardingDraft
}

let pool: Pool | null = null
let schemaReady = false

function getDatabaseUrl(): string {
  const configured =
    process.env.FRONTEND_DATABASE_URL ||
    process.env.DATABASE_URL ||
    process.env.DF_POSTGRES_URL ||
    "postgresql://stratos:password@localhost:5432/stratos"

  return configured.replace("postgresql+asyncpg://", "postgresql://")
}

function getPool(): Pool {
  if (!pool) {
    pool = new Pool({
      connectionString: getDatabaseUrl(),
    })
  }

  return pool
}

export async function ensureLocalAuthSchema(): Promise<void> {
  if (schemaReady) {
    return
  }

  const client = await getPool().connect()
  try {
    await client.query(`
      CREATE TABLE IF NOT EXISTS local_users (
        id TEXT PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      );

      CREATE TABLE IF NOT EXISTS local_sessions (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES local_users(id) ON DELETE CASCADE,
        expires_at TIMESTAMPTZ NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      );

      CREATE TABLE IF NOT EXISTS local_user_state (
        user_id TEXT PRIMARY KEY REFERENCES local_users(id) ON DELETE CASCADE,
        workspace_json JSONB NOT NULL,
        draft_json JSONB NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      );

      CREATE INDEX IF NOT EXISTS idx_local_sessions_user_id ON local_sessions(user_id);
      CREATE INDEX IF NOT EXISTS idx_local_sessions_expires_at ON local_sessions(expires_at);
    `)
    schemaReady = true
  } finally {
    client.release()
  }
}

function hashPassword(password: string): string {
  const salt = randomBytes(16)
  const derived = scryptSync(password, salt, 64)
  return `${salt.toString("base64url")}:${derived.toString("base64url")}`
}

function verifyPassword(password: string, storedHash: string): boolean {
  const [salt, hash] = storedHash.split(":")
  if (!salt || !hash) {
    return false
  }

  const derived = scryptSync(password, Buffer.from(salt, "base64url"), 64)
  return timingSafeEqual(derived, Buffer.from(hash, "base64url"))
}

export async function createLocalUser(input: {
  email: string
  name: string
  password: string
}): Promise<UserRow> {
  await ensureLocalAuthSchema()
  const normalizedEmail = input.email.trim().toLowerCase()
  const name = input.name.trim() || normalizedEmail.split("@")[0] || "STRATOS User"
  const user = await getPool().query<UserRow>(
    `
      INSERT INTO local_users (id, email, name, password_hash)
      VALUES ($1, $2, $3, $4)
      RETURNING id, email, name, password_hash, created_at
    `,
    [randomUUID(), normalizedEmail, name, hashPassword(input.password)]
  )

  return user.rows[0]
}

export async function findLocalUserByEmail(email: string): Promise<UserRow | null> {
  await ensureLocalAuthSchema()
  const result = await getPool().query<UserRow>(
    `
      SELECT id, email, name, password_hash, created_at
      FROM local_users
      WHERE email = $1
      LIMIT 1
    `,
    [email.trim().toLowerCase()]
  )

  return result.rows[0] ?? null
}

export async function verifyLocalUser(email: string, password: string): Promise<UserRow | null> {
  const user = await findLocalUserByEmail(email)
  if (!user || !verifyPassword(password, user.password_hash)) {
    return null
  }

  return user
}

export async function createLocalSession(input: {
  userId: string
  email: string
  name: string
  rememberMe: boolean
}): Promise<AppSession> {
  await ensureLocalAuthSchema()
  const token = `dbs_${randomBytes(24).toString("base64url")}`
  const now = new Date()
  const durationMs = input.rememberMe ? 1000 * 60 * 60 * 24 * 30 : 1000 * 60 * 60 * 8
  const expiresAt = new Date(now.getTime() + durationMs)

  await getPool().query(
    `
      INSERT INTO local_sessions (id, user_id, expires_at)
      VALUES ($1, $2, $3)
    `,
    [token, input.userId, expiresAt.toISOString()]
  )

  return {
    userId: input.userId,
    name: input.name,
    email: input.email,
    source: "local",
    sessionId: token,
    expiresAt: expiresAt.toISOString(),
    createdAt: now.toISOString(),
  }
}

export async function getLocalSession(token: string): Promise<AppSession | null> {
  await ensureLocalAuthSchema()
  const result = await getPool().query<SessionRow>(
    `
      SELECT s.id, s.user_id, s.expires_at, s.created_at, u.email, u.name
      FROM local_sessions s
      JOIN local_users u ON u.id = s.user_id
      WHERE s.id = $1
      LIMIT 1
    `,
    [token]
  )

  const row = result.rows[0]
  if (!row) {
    return null
  }

  if (row.expires_at.getTime() <= Date.now()) {
    await deleteLocalSession(token)
    return null
  }

  return {
    userId: row.user_id,
    name: row.name,
    email: row.email,
    source: "local",
    sessionId: row.id,
    expiresAt: row.expires_at.toISOString(),
    createdAt: row.created_at.toISOString(),
  }
}

export async function deleteLocalSession(token: string): Promise<void> {
  await ensureLocalAuthSchema()
  await getPool().query(`DELETE FROM local_sessions WHERE id = $1`, [token])
}

export async function getLocalUserState(userId: string): Promise<UserStateRow | null> {
  await ensureLocalAuthSchema()
  const result = await getPool().query<UserStateRow>(
    `
      SELECT workspace_json, draft_json
      FROM local_user_state
      WHERE user_id = $1
      LIMIT 1
    `,
    [userId]
  )

  return result.rows[0] ?? null
}

export async function upsertLocalUserState(
  userId: string,
  workspace: WorkspaceState,
  draft: OnboardingDraft
): Promise<void> {
  await ensureLocalAuthSchema()
  await getPool().query(
    `
      INSERT INTO local_user_state (user_id, workspace_json, draft_json, updated_at)
      VALUES ($1, $2::jsonb, $3::jsonb, NOW())
      ON CONFLICT (user_id)
      DO UPDATE SET
        workspace_json = EXCLUDED.workspace_json,
        draft_json = EXCLUDED.draft_json,
        updated_at = NOW()
    `,
    [userId, JSON.stringify(workspace), JSON.stringify(draft)]
  )
}
