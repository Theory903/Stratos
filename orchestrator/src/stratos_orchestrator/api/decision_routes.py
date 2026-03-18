"""Decision tracking API routes."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Callable

router = APIRouter(prefix="/decisions", tags=["Decisions"])


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _encode_datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


class DecisionCreate(BaseModel):
    workspace_id: str
    thread_id: str | None = None
    run_id: str | None = None
    type: str = "run"
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] | None = None
    status: str = "pending"
    confidence_score: float | None = None
    risk_band: str | None = None
    linked_positions: list[str] = Field(default_factory=list)
    linked_events: list[str] = Field(default_factory=list)
    linked_briefs: list[str] = Field(default_factory=list)
    created_by: str | None = None
    note: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DecisionUpdate(BaseModel):
    status: str | None = None
    note: str | None = None
    outputs: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class DecisionResponse(BaseModel):
    id: str
    workspace_id: str
    thread_id: str | None
    run_id: str | None
    type: str
    inputs: dict[str, Any]
    outputs: dict[str, Any] | None
    status: str
    confidence_score: float | None
    risk_band: str | None
    linked_positions: list[str]
    linked_events: list[str]
    linked_briefs: list[str]
    created_by: str | None
    created_at: str
    decided_at: str | None
    note: str | None
    metadata: dict[str, Any]


class DecisionStore:
    """SQLite-backed decision store."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, path: str | Path = ".stratos/decisions.db"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, path: str | Path = ".stratos/decisions.db") -> None:
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
                CREATE TABLE IF NOT EXISTS decisions (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    thread_id TEXT,
                    run_id TEXT,
                    type TEXT NOT NULL,
                    inputs TEXT NOT NULL,
                    outputs TEXT,
                    status TEXT NOT NULL,
                    confidence_score REAL,
                    risk_band TEXT,
                    linked_positions TEXT NOT NULL,
                    linked_events TEXT NOT NULL,
                    linked_briefs TEXT NOT NULL,
                    created_by TEXT,
                    created_at TEXT NOT NULL,
                    decided_at TEXT,
                    note TEXT,
                    metadata TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_decisions_workspace 
                    ON decisions(workspace_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_decisions_thread 
                    ON decisions(thread_id);
                CREATE INDEX IF NOT EXISTS idx_decisions_type 
                    ON decisions(workspace_id, type, status);
                """
            )

    def create(self, data: DecisionCreate) -> DecisionResponse:
        decision_id = str(uuid4())
        now = _encode_datetime(_utcnow())

        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO decisions 
                (id, workspace_id, thread_id, run_id, type, inputs, outputs, status,
                 confidence_score, risk_band, linked_positions, linked_events, linked_briefs,
                 created_by, created_at, decided_at, note, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision_id,
                    data.workspace_id,
                    data.thread_id,
                    data.run_id,
                    data.type,
                    json.dumps(data.inputs),
                    json.dumps(data.outputs) if data.outputs else None,
                    data.status,
                    data.confidence_score,
                    data.risk_band,
                    json.dumps(data.linked_positions),
                    json.dumps(data.linked_events),
                    json.dumps(data.linked_briefs),
                    data.created_by,
                    now,
                    None,
                    data.note,
                    json.dumps(data.metadata),
                ),
            )

        return self._row_to_response({
            "id": decision_id,
            "workspace_id": data.workspace_id,
            "thread_id": data.thread_id,
            "run_id": data.run_id,
            "type": data.type,
            "inputs": data.inputs,
            "outputs": data.outputs,
            "status": data.status,
            "confidence_score": data.confidence_score,
            "risk_band": data.risk_band,
            "linked_positions": data.linked_positions,
            "linked_events": data.linked_events,
            "linked_briefs": data.linked_briefs,
            "created_by": data.created_by,
            "created_at": now,
            "decided_at": None,
            "note": data.note,
            "metadata": data.metadata,
        })

    def list(
        self,
        workspace_id: str,
        type: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DecisionResponse]:
        query = "SELECT * FROM decisions WHERE workspace_id = ?"
        params: list[Any] = [workspace_id]

        if type:
            query += " AND type = ?"
            params.append(type)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._lock:
            rows = self._conn.execute(query, params).fetchall()

        return [self._row_to_response(dict(row)) for row in rows]

    def get(self, decision_id: str) -> DecisionResponse | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM decisions WHERE id = ?",
                (decision_id,),
            ).fetchone()

        return self._row_to_response(dict(row)) if row else None

    def update(self, decision_id: str, data: DecisionUpdate) -> DecisionResponse | None:
        updates: list[str] = []
        params: list[Any] = []

        if data.status is not None:
            updates.append("status = ?")
            params.append(data.status)
            if data.status in ("approved", "rejected", "superseded"):
                updates.append("decided_at = ?")
                params.append(_encode_datetime(_utcnow()))

        if data.note is not None:
            updates.append("note = ?")
            params.append(data.note)

        if data.outputs is not None:
            updates.append("outputs = ?")
            params.append(json.dumps(data.outputs))

        if data.metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(data.metadata))

        if not updates:
            return self.get(decision_id)

        params.append(decision_id)
        query = f"UPDATE decisions SET {', '.join(updates)} WHERE id = ?"

        with self._lock:
            self._conn.execute(query, params)

        return self.get(decision_id)

    def history(
        self,
        workspace_id: str,
        position: str | None = None,
        event: str | None = None,
        since: str | None = None,
        limit: int = 50,
    ) -> list[DecisionResponse]:
        query = "SELECT * FROM decisions WHERE workspace_id = ?"
        params: list[Any] = [workspace_id]

        if position:
            query += " AND linked_positions LIKE ?"
            params.append(f'%"{position}"%')
        if event:
            query += " AND linked_events LIKE ?"
            params.append(f'%"{event}"%')
        if since:
            query += " AND created_at >= ?"
            params.append(since)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            rows = self._conn.execute(query, params).fetchall()

        return [self._row_to_response(dict(row)) for row in rows]

    def _row_to_response(self, row: dict[str, Any]) -> DecisionResponse:
        return DecisionResponse(
            id=row["id"],
            workspace_id=row["workspace_id"],
            thread_id=row["thread_id"],
            run_id=row["run_id"],
            type=row["type"],
            inputs=json.loads(row["inputs"]),
            outputs=json.loads(row["outputs"]) if row["outputs"] else None,
            status=row["status"],
            confidence_score=row["confidence_score"],
            risk_band=row["risk_band"],
            linked_positions=json.loads(row["linked_positions"]),
            linked_events=json.loads(row["linked_events"]),
            linked_briefs=json.loads(row["linked_briefs"]),
            created_by=row["created_by"],
            created_at=row["created_at"],
            decided_at=row["decided_at"],
            note=row["note"],
            metadata=json.loads(row["metadata"]),
        )


_decision_store: DecisionStore | None = None


def get_decision_store() -> DecisionStore:
    global _decision_store
    if _decision_store is None:
        _decision_store = DecisionStore()
    return _decision_store


@router.post("", response_model=DecisionResponse)
async def create_decision(
    data: DecisionCreate,
    store: DecisionStore = Depends(get_decision_store),
) -> DecisionResponse:
    """Create a new decision record."""
    return store.create(data)


@router.get("", response_model=list[DecisionResponse])
async def list_decisions(
    workspace_id: str,
    type: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    store: DecisionStore = Depends(get_decision_store),
) -> list[DecisionResponse]:
    """List decisions for workspace with filtering."""
    return store.list(workspace_id, type, status, limit, offset)


@router.get("/{decision_id}", response_model=DecisionResponse)
async def get_decision(
    decision_id: str,
    store: DecisionStore = Depends(get_decision_store),
) -> DecisionResponse:
    """Get single decision with full context."""
    decision = store.get(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision


@router.put("/{decision_id}", response_model=DecisionResponse)
async def update_decision(
    decision_id: str,
    data: DecisionUpdate,
    store: DecisionStore = Depends(get_decision_store),
) -> DecisionResponse:
    """Update decision status (approve/reject/supersede) or add notes."""
    decision = store.update(decision_id, data)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision


@router.get("/history/list", response_model=list[DecisionResponse])
async def decision_history(
    workspace_id: str,
    position: str | None = None,
    event: str | None = None,
    since: str | None = None,
    limit: int = 50,
    store: DecisionStore = Depends(get_decision_store),
) -> list[DecisionResponse]:
    """Get decision history linked to position or event."""
    return store.history(workspace_id, position, event, since, limit)


@router.get("/queue/pending", response_model=list[DecisionResponse])
async def pending_decisions(
    workspace_id: str,
    store: DecisionStore = Depends(get_decision_store),
) -> list[DecisionResponse]:
    """Get all pending decisions for workspace."""
    return store.list(workspace_id, status="pending", limit=100)
