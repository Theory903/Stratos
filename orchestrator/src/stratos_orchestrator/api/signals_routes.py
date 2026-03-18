"""Signals aggregation API routes for role-aware signal ranking."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

router = APIRouter(prefix="/signals", tags=["Signals"])


class WorkspaceRole(str, Enum):
    PM = "pm"
    ANALYST = "analyst"
    CFO = "cfo"
    CEO = "ceo"


class SignalType(str, Enum):
    RISK = "risk"
    OPPORTUNITY = "opportunity"
    EVENT = "event"
    MARKET = "market"
    RESEARCH = "research"


class SignalItem(BaseModel):
    signal_id: str
    type: SignalType
    title: str
    detail: str
    urgency: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    freshness: str = "fresh"  # 'fresh' | 'stale'
    linked_entities: dict[str, list[str]] = Field(default_factory=dict)
    score: float = Field(ge=0, le=1)
    created_at: str


class SignalCreate(BaseModel):
    workspace_id: str
    type: SignalType
    title: str
    detail: str
    urgency: float = 0.5
    confidence: float = 0.5
    linked_positions: list[str] = Field(default_factory=list)
    linked_events: list[str] = Field(default_factory=list)
    linked_briefs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _encode_datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


class SignalStore:
    """SQLite-backed signal store with role-aware scoring."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, path: str | Path = ".stratos/signals.db"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, path: str | Path = ".stratos/signals.db") -> None:
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
                CREATE TABLE IF NOT EXISTS signals (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    urgency REAL NOT NULL,
                    confidence REAL NOT NULL,
                    freshness TEXT NOT NULL DEFAULT 'fresh',
                    linked_positions TEXT NOT NULL,
                    linked_events TEXT NOT NULL,
                    linked_briefs TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_signals_workspace 
                    ON signals(workspace_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_signals_type 
                    ON signals(workspace_id, type);
                CREATE INDEX IF NOT EXISTS idx_signals_expires 
                    ON signals(expires_at);
                """
            )

    def create(self, data: SignalCreate, ttl_minutes: int = 60) -> SignalItem:
        signal_id = str(uuid4())
        now = _encode_datetime(_utcnow())
        expires_at = _encode_datetime(_utcnow().__class__.fromtimestamp(
            _utcnow().timestamp() + ttl_minutes * 60
        ))

        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO signals 
                (id, workspace_id, type, title, detail, urgency, confidence, freshness,
                 linked_positions, linked_events, linked_briefs, metadata, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    data.workspace_id,
                    data.type.value,
                    data.title,
                    data.detail,
                    data.urgency,
                    data.confidence,
                    "fresh",
                    json.dumps(data.linked_positions),
                    json.dumps(data.linked_events),
                    json.dumps(data.linked_briefs),
                    json.dumps(data.metadata),
                    now,
                    expires_at,
                ),
            )

        return SignalItem(
            signal_id=signal_id,
            type=data.type,
            title=data.title,
            detail=data.detail,
            urgency=data.urgency,
            confidence=data.confidence,
            freshness="fresh",
            linked_entities={
                "positions": data.linked_positions,
                "events": data.linked_events,
                "briefs": data.linked_briefs,
            },
            score=self._score_signal(data.urgency, data.confidence, WorkspaceRole.PM),
            created_at=now,
        )

    def _score_signal(
        self,
        urgency: float,
        confidence: float,
        role: WorkspaceRole,
        recency_decay: float = 1.0,
    ) -> float:
        """
        Score a signal based on role.

        PM: weight = urgency(0.6) + confidence(0.3) + recency(0.1)
        Analyst: weight = confidence(0.5) + freshness(0.3) + recency(0.2)
        CFO: weight = urgency(0.7) + risk(0.2) + recency(0.1)
        CEO: weight = urgency(0.5) + macro_relevance(0.3) + recency(0.2)
        """
        if role == WorkspaceRole.PM:
            return urgency * 0.6 + confidence * 0.3 + recency_decay * 0.1
        elif role == WorkspaceRole.ANALYST:
            return confidence * 0.5 + urgency * 0.3 + recency_decay * 0.2
        elif role == WorkspaceRole.CFO:
            return urgency * 0.7 + confidence * 0.2 + recency_decay * 0.1
        elif role == WorkspaceRole.CEO:
            return urgency * 0.5 + confidence * 0.3 + recency_decay * 0.2
        return urgency * 0.4 + confidence * 0.4 + recency_decay * 0.2

    def list_signals(
        self,
        workspace_id: str,
        role: WorkspaceRole = WorkspaceRole.PM,
        signal_type: SignalType | None = None,
        focus: str | None = None,
        limit: int = 50,
    ) -> list[SignalItem]:
        now = _encode_datetime(_utcnow())

        query = """
            SELECT * FROM signals 
            WHERE workspace_id = ? 
            AND (expires_at IS NULL OR expires_at > ?)
        """
        params: list[Any] = [workspace_id, now]

        if signal_type:
            query += " AND type = ?"
            params.append(signal_type.value)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            rows = self._conn.execute(query, params).fetchall()

        signals = []
        for row in rows:
            signal = self._row_to_item(dict(row))
            signal.score = self._calculate_score(signal, role)
            signals.append(signal)

        signals.sort(key=lambda s: s.score, reverse=True)
        return signals[:limit]

    def _calculate_score(self, signal: SignalItem, role: WorkspaceRole) -> float:
        freshness_score = 1.0 if signal.freshness == "fresh" else 0.5
        return self._score_signal(signal.urgency, signal.confidence, role, freshness_score)

    def _row_to_item(self, row: dict[str, Any]) -> SignalItem:
        return SignalItem(
            signal_id=row["id"],
            type=SignalType(row["type"]),
            title=row["title"],
            detail=row["detail"],
            urgency=row["urgency"],
            confidence=row["confidence"],
            freshness=row["freshness"],
            linked_entities={
                "positions": json.loads(row["linked_positions"]),
                "events": json.loads(row["linked_events"]),
                "briefs": json.loads(row["linked_briefs"]),
            },
            score=0,
            created_at=row["created_at"],
        )

    def cleanup_expired(self) -> int:
        now = _encode_datetime(_utcnow())
        with self._lock:
            cursor = self._conn.execute(
                "DELETE FROM signals WHERE expires_at IS NOT NULL AND expires_at < ?",
                (now,),
            )
            self._conn.commit()
            return cursor.rowcount


_signal_store: SignalStore | None = None


def get_signal_store() -> SignalStore:
    global _signal_store
    if _signal_store is None:
        _signal_store = SignalStore()
    return _signal_store


@router.get("/overview", response_model=list[SignalItem])
async def get_signals_overview(
    workspace_id: str,
    role: WorkspaceRole = WorkspaceRole.PM,
    focus: str | None = None,
    limit: int = 20,
    store: SignalStore = Depends(get_signal_store),
) -> list[SignalItem]:
    """Aggregated signals for Overview page, role-aware weighting."""
    signal_type = None
    if focus == "portfolio":
        signal_type = SignalType.RISK
    elif focus == "research":
        signal_type = SignalType.RESEARCH
    elif focus == "events":
        signal_type = SignalType.EVENT

    return store.list_signals(workspace_id, role, signal_type, focus, limit)


@router.get("/attention", response_model=list[SignalItem])
async def get_attention_queue(
    workspace_id: str,
    role: WorkspaceRole = WorkspaceRole.PM,
    limit: int = 10,
    store: SignalStore = Depends(get_signal_store),
) -> list[SignalItem]:
    """Prioritized attention list — top signals by urgency + relevance."""
    return store.list_signals(workspace_id, role, None, None, limit)


@router.post("", response_model=SignalItem)
async def create_signal(
    data: SignalCreate,
    ttl_minutes: int = 60,
    store: SignalStore = Depends(get_signal_store),
) -> SignalItem:
    """Create a new signal."""
    return store.create(data, ttl_minutes)


@router.delete("/cleanup")
async def cleanup_expired_signals(
    store: SignalStore = Depends(get_signal_store),
) -> dict:
    """Remove expired signals from store."""
    if store is None:
        store = get_signal_store()
    count = store.cleanup_expired()
    return {"deleted": count}
