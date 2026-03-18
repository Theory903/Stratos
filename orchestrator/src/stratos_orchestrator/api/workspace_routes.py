"""Workspace and multi-tenant membership API routes."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _encode_datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


class WorkspaceCreate(BaseModel):
    name: str
    owner_id: str
    benchmark: str = "SPY"
    markets: list[str] = Field(default_factory=lambda: ["US", "India", "BTC"])
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkspaceUpdate(BaseModel):
    name: str | None = None
    benchmark: str | None = None
    markets: list[str] | None = None
    metadata: dict[str, Any] | None = None


class WorkspaceMemberAdd(BaseModel):
    user_id: str
    email: str
    name: str
    role: str = "member"  # owner, member, viewer


class WorkspaceMemberUpdate(BaseModel):
    role: str | None = None


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    owner_id: str
    benchmark: str
    markets: list[str]
    member_count: int
    created_at: str
    updated_at: str
    metadata: dict[str, Any]


class WorkspaceMemberResponse(BaseModel):
    workspace_id: str
    user_id: str
    email: str
    name: str
    role: str
    joined_at: str


class WorkspaceStore:
    """SQLite-backed workspace store with membership support."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, path: str | Path = ".stratos/workspaces.db"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, path: str | Path = ".stratos/workspaces.db") -> None:
        if getattr(self, "_initialized", False):
            return
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()
        self._initialized = True

    def _init_db(self) -> None:
        with self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS workspaces (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    benchmark TEXT NOT NULL DEFAULT 'SPY',
                    markets TEXT NOT NULL DEFAULT '["US", "India", "BTC"]',
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS workspace_members (
                    workspace_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    email TEXT NOT NULL,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'member',
                    joined_at TEXT NOT NULL,
                    PRIMARY KEY (workspace_id, user_id)
                );

                CREATE INDEX IF NOT EXISTS idx_workspaces_owner ON workspaces(owner_id);
                CREATE INDEX IF NOT EXISTS idx_workspace_members_user ON workspace_members(user_id);
                CREATE INDEX IF NOT EXISTS idx_workspace_members_workspace ON workspace_members(workspace_id);
                """
            )

    def create_workspace(self, data: WorkspaceCreate) -> WorkspaceResponse:
        workspace_id = str(uuid4())
        now = _encode_datetime(_utcnow())

        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO workspaces (id, name, owner_id, benchmark, markets, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    workspace_id,
                    data.name,
                    data.owner_id,
                    data.benchmark,
                    json.dumps(data.markets),
                    json.dumps(data.metadata),
                    now,
                    now,
                ),
            )

            self._conn.execute(
                """
                INSERT INTO workspace_members (workspace_id, user_id, email, name, role, joined_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (workspace_id, data.owner_id, "", data.name or "Owner", "owner", now),
            )

        return self.get_workspace(workspace_id)

    def get_workspace(self, workspace_id: str) -> WorkspaceResponse | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM workspaces WHERE id = ?",
                (workspace_id,),
            ).fetchone()

        if not row:
            return None

        member_count = self._conn.execute(
            "SELECT COUNT(*) FROM workspace_members WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()[0]

        return WorkspaceResponse(
            id=row["id"],
            name=row["name"],
            owner_id=row["owner_id"],
            benchmark=row["benchmark"],
            markets=json.loads(row["markets"]),
            member_count=member_count,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            metadata=json.loads(row["metadata"]),
        )

    def list_user_workspaces(self, user_id: str) -> list[WorkspaceResponse]:
        """List all workspaces a user has access to."""
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT w.id FROM workspaces w
                JOIN workspace_members m ON w.id = m.workspace_id
                WHERE m.user_id = ?
                ORDER BY m.joined_at DESC
                """,
                (user_id,),
            ).fetchall()

        workspaces = []
        for row in rows:
            ws = self.get_workspace(row["id"])
            if ws:
                workspaces.append(ws)

        return workspaces

    def update_workspace(self, workspace_id: str, user_id: str, data: WorkspaceUpdate) -> WorkspaceResponse | None:
        """Update workspace if user is owner."""
        with self._lock:
            workspace = self._conn.execute(
                "SELECT * FROM workspaces WHERE id = ?",
                (workspace_id,),
            ).fetchone()

        if not workspace:
            return None

        if workspace["owner_id"] != user_id:
            raise HTTPException(status_code=403, detail="Only owner can update workspace")

        updates = []
        params = []

        if data.name is not None:
            updates.append("name = ?")
            params.append(data.name)
        if data.benchmark is not None:
            updates.append("benchmark = ?")
            params.append(data.benchmark)
        if data.markets is not None:
            updates.append("markets = ?")
            params.append(json.dumps(data.markets))
        if data.metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(data.metadata))

        if not updates:
            return self.get_workspace(workspace_id)

        updates.append("updated_at = ?")
        params.append(_encode_datetime(_utcnow()))
        params.append(workspace_id)

        with self._lock:
            self._conn.execute(
                f"UPDATE workspaces SET {', '.join(updates)} WHERE id = ?",
                params,
            )

        return self.get_workspace(workspace_id)

    def add_member(self, workspace_id: str, user_id: str, data: WorkspaceMemberAdd) -> WorkspaceMemberResponse | None:
        """Add member to workspace if requester is owner."""
        with self._lock:
            workspace = self._conn.execute(
                "SELECT * FROM workspaces WHERE id = ?",
                (workspace_id,),
            ).fetchone()

        if not workspace:
            return None

        if workspace["owner_id"] != user_id:
            raise HTTPException(status_code=403, detail="Only owner can add members")

        existing = self._conn.execute(
            "SELECT 1 FROM workspace_members WHERE workspace_id = ? AND user_id = ?",
            (workspace_id, data.user_id),
        ).fetchone()

        if existing:
            raise HTTPException(status_code=409, detail="User already a member")

        now = _encode_datetime(_utcnow())
        self._conn.execute(
            """
            INSERT INTO workspace_members (workspace_id, user_id, email, name, role, joined_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (workspace_id, data.user_id, data.email, data.name, data.role, now),
        )

        return WorkspaceMemberResponse(
            workspace_id=workspace_id,
            user_id=data.user_id,
            email=data.email,
            name=data.name,
            role=data.role,
            joined_at=now,
        )

    def list_members(self, workspace_id: str, user_id: str) -> list[WorkspaceMemberResponse]:
        """List all members of a workspace."""
        with self._lock:
            member = self._conn.execute(
                "SELECT 1 FROM workspace_members WHERE workspace_id = ? AND user_id = ?",
                (workspace_id, user_id),
            ).fetchone()

        if not member:
            raise HTTPException(status_code=403, detail="Not a member of workspace")

        rows = self._conn.execute(
            "SELECT * FROM workspace_members WHERE workspace_id = ? ORDER BY joined_at",
            (workspace_id,),
        ).fetchall()

        return [
            WorkspaceMemberResponse(
                workspace_id=row["workspace_id"],
                user_id=row["user_id"],
                email=row["email"],
                name=row["name"],
                role=row["role"],
                joined_at=row["joined_at"],
            )
            for row in rows
        ]

    def remove_member(self, workspace_id: str, requester_id: str, target_user_id: str) -> bool:
        """Remove member from workspace."""
        with self._lock:
            workspace = self._conn.execute(
                "SELECT * FROM workspaces WHERE id = ?",
                (workspace_id,),
            ).fetchone()

        if not workspace:
            return False

        if workspace["owner_id"] != requester_id and requester_id != target_user_id:
            raise HTTPException(status_code=403, detail="Cannot remove this member")

        if workspace["owner_id"] == target_user_id:
            raise HTTPException(status_code=400, detail="Cannot remove owner")

        self._conn.execute(
            "DELETE FROM workspace_members WHERE workspace_id = ? AND user_id = ?",
            (workspace_id, target_user_id),
        )
        return True

    def check_access(self, workspace_id: str, user_id: str) -> bool:
        """Check if user has access to workspace."""
        with self._lock:
            member = self._conn.execute(
                "SELECT 1 FROM workspace_members WHERE workspace_id = ? AND user_id = ?",
                (workspace_id, user_id),
            ).fetchone()
        return member is not None


_workspace_store: WorkspaceStore | None = None


def get_workspace_store() -> WorkspaceStore:
    global _workspace_store
    if _workspace_store is None:
        _workspace_store = WorkspaceStore()
    return _workspace_store


WorkspaceStoreDep = Depends(get_workspace_store)


@router.post("", response_model=WorkspaceResponse)
async def create_workspace(
    data: WorkspaceCreate,
    store = WorkspaceStoreDep,
) -> WorkspaceResponse:
    """Create a new workspace."""
    return store.create_workspace(data)


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    user_id: str,
    store = WorkspaceStoreDep,
) -> list[WorkspaceResponse]:
    """List all workspaces for a user. If user_id is 'current' and no workspaces exist, creates a default one."""
    if user_id == "current":
        workspaces = store.list_user_workspaces(user_id)
        if not workspaces:
            default_workspace = store.create_workspace(WorkspaceCreate(
                name="My Workspace",
                owner_id="current",
                benchmark="SPY",
                markets=["US", "India", "BTC"],
            ))
            workspaces = [default_workspace]
        return workspaces
    return store.list_user_workspaces(user_id)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    user_id: str,
    store = WorkspaceStoreDep,
) -> WorkspaceResponse:
    """Get workspace if user has access. If workspace_id is 'default', returns first accessible workspace."""
    if workspace_id == "default":
        workspaces = store.list_user_workspaces(user_id)
        if workspaces:
            return workspaces[0]
        if user_id == "current":
            default_workspace = store.create_workspace(WorkspaceCreate(
                name="My Workspace",
                owner_id="current",
                benchmark="SPY",
                markets=["US", "India", "BTC"],
            ))
            return default_workspace
        raise HTTPException(status_code=404, detail="No workspaces found")
    if not store.check_access(workspace_id, user_id):
        raise HTTPException(status_code=403, detail="Access denied")
    workspace = store.get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.put("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: str,
    user_id: str,
    data: WorkspaceUpdate,
    store = WorkspaceStoreDep,
) -> WorkspaceResponse:
    """Update workspace (owner only)."""
    resolved_id = _resolve_workspace_id(workspace_id, user_id, store)
    workspace = store.update_workspace(resolved_id, user_id, data)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


def _resolve_workspace_id(workspace_id: str, user_id: str, store: WorkspaceStore) -> str:
    """Resolve 'default' workspace_id to actual workspace ID."""
    if workspace_id != "default":
        return workspace_id
    workspaces = store.list_user_workspaces(user_id)
    if workspaces:
        return workspaces[0].id
    if user_id == "current":
        default_workspace = store.create_workspace(WorkspaceCreate(
            name="My Workspace",
            owner_id="current",
            benchmark="SPY",
            markets=["US", "India", "BTC"],
        ))
        return default_workspace.id
    raise HTTPException(status_code=404, detail="No workspace found")


@router.post("/{workspace_id}/members", response_model=WorkspaceMemberResponse)
async def add_member(
    workspace_id: str,
    user_id: str,
    data: WorkspaceMemberAdd,
    store = WorkspaceStoreDep,
) -> WorkspaceMemberResponse:
    """Add member to workspace (owner only)."""
    resolved_id = _resolve_workspace_id(workspace_id, user_id, store)
    member = store.add_member(resolved_id, user_id, data)
    if not member:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return member


@router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberResponse])
async def list_members(
    workspace_id: str,
    user_id: str,
    store = WorkspaceStoreDep,
) -> list[WorkspaceMemberResponse]:
    """List workspace members."""
    resolved_id = _resolve_workspace_id(workspace_id, user_id, store)
    return store.list_members(resolved_id, user_id)


@router.delete("/{workspace_id}/members/{target_user_id}")
async def remove_member(
    workspace_id: str,
    user_id: str,
    target_user_id: str,
    store = WorkspaceStoreDep,
) -> dict:
    """Remove member from workspace."""
    resolved_id = _resolve_workspace_id(workspace_id, user_id, store)
    success = store.remove_member(resolved_id, user_id, target_user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"ok": True}


class AlertSettings(BaseModel):
    macro_pressure: bool = True
    concentration_threshold: float = 0.15
    event_urgency_min: float = 0.7
    approval_notify: bool = True


@router.get("/{workspace_id}/check-access")
async def check_access(
    workspace_id: str,
    user_id: str,
    store = WorkspaceStoreDep,
) -> dict:
    """Check if user has access to workspace."""
    has_access = store.check_access(workspace_id, user_id)
    return {"has_access": has_access}


@router.get("/{workspace_id}/alerts", response_model=AlertSettings)
async def get_alerts(
    workspace_id: str,
    user_id: str,
    store = WorkspaceStoreDep,
) -> AlertSettings:
    """Get workspace alert settings."""
    resolved_id = _resolve_workspace_id(workspace_id, user_id, store)
    workspace = store.get_workspace(resolved_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    alerts_data = workspace.metadata.get("alerts", {})
    return AlertSettings(**{k: alerts_data.get(k, getattr(AlertSettings(), k)) for k in AlertSettings.model_fields})


@router.put("/{workspace_id}/alerts", response_model=AlertSettings)
async def update_alerts(
    workspace_id: str,
    user_id: str,
    data: AlertSettings,
    store = WorkspaceStoreDep,
) -> AlertSettings:
    """Update workspace alert settings (owner only)."""
    resolved_id = _resolve_workspace_id(workspace_id, user_id, store)
    workspace = store.get_workspace(resolved_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if workspace.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Only owner can update alerts")
    with store._lock, store._conn:
        store._conn.execute(
            "UPDATE workspaces SET metadata = json_set(metadata, '$.alerts', ?), updated_at = ? WHERE id = ?",
            (json.dumps(data.model_dump()), _encode_datetime(_utcnow()), resolved_id),
        )
    return data
