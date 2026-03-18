"""Durable local persistence adapters for LangGraph runtime state."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from langgraph.checkpoint.memory import WRITES_IDX_MAP, get_checkpoint_id, get_checkpoint_metadata
from langgraph.store.base import BaseStore, GetOp, Item, ListNamespacesOp, PutOp, Result, SearchItem, SearchOp


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _encode_namespace(namespace: tuple[str, ...]) -> str:
    return json.dumps(list(namespace), separators=(",", ":"))


def _decode_namespace(value: str) -> tuple[str, ...]:
    return tuple(json.loads(value))


def _encode_datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _decode_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


class SqliteCheckpointSaver(BaseCheckpointSaver[str]):
    """SQLite-backed checkpoint saver for durable local LangGraph execution."""

    def __init__(self, path: str | Path) -> None:
        super().__init__()
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        with self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS checkpoints (
                    thread_id TEXT NOT NULL,
                    checkpoint_ns TEXT NOT NULL,
                    checkpoint_id TEXT NOT NULL,
                    checkpoint_type TEXT NOT NULL,
                    checkpoint_blob BLOB NOT NULL,
                    metadata_type TEXT NOT NULL,
                    metadata_blob BLOB NOT NULL,
                    parent_checkpoint_id TEXT,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
                );

                CREATE TABLE IF NOT EXISTS checkpoint_blobs (
                    thread_id TEXT NOT NULL,
                    checkpoint_ns TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    version TEXT NOT NULL,
                    value_type TEXT NOT NULL,
                    value_blob BLOB NOT NULL,
                    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
                );

                CREATE TABLE IF NOT EXISTS checkpoint_writes (
                    thread_id TEXT NOT NULL,
                    checkpoint_ns TEXT NOT NULL,
                    checkpoint_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    idx INTEGER NOT NULL,
                    channel TEXT NOT NULL,
                    value_type TEXT NOT NULL,
                    value_blob BLOB NOT NULL,
                    task_path TEXT NOT NULL,
                    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
                );
                """
            )

    def _loads(self, type_tag: str, payload: bytes) -> Any:
        return self.serde.loads_typed((type_tag, payload))

    def _load_blobs(self, thread_id: str, checkpoint_ns: str, versions: ChannelVersions) -> dict[str, Any]:
        if not versions:
            return {}
        clauses = []
        params: list[Any] = [thread_id, checkpoint_ns]
        for channel, version in versions.items():
            clauses.append("(channel = ? AND version = ?)")
            params.extend([channel, str(version)])
        query = (
            "SELECT channel, value_type, value_blob FROM checkpoint_blobs "
            "WHERE thread_id = ? AND checkpoint_ns = ? AND (" + " OR ".join(clauses) + ")"
        )
        channel_values: dict[str, Any] = {}
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        for row in rows:
            if row["value_type"] == "empty":
                continue
            channel_values[row["channel"]] = self._loads(row["value_type"], row["value_blob"])
        return channel_values

    def _row_to_tuple(self, row: sqlite3.Row) -> CheckpointTuple:
        thread_id = row["thread_id"]
        checkpoint_ns = row["checkpoint_ns"]
        checkpoint_id = row["checkpoint_id"]
        checkpoint = self._loads(row["checkpoint_type"], row["checkpoint_blob"])
        metadata = self._loads(row["metadata_type"], row["metadata_blob"])
        checkpoint_with_values = {
            **checkpoint,
            "channel_values": self._load_blobs(thread_id, checkpoint_ns, checkpoint["channel_versions"]),
        }
        with self._lock:
            write_rows = self._conn.execute(
                """
                SELECT task_id, channel, value_type, value_blob
                FROM checkpoint_writes
                WHERE thread_id = ? AND checkpoint_ns = ? AND checkpoint_id = ?
                ORDER BY idx ASC
                """,
                (thread_id, checkpoint_ns, checkpoint_id),
            ).fetchall()
        pending_writes = [
            (write_row["task_id"], write_row["channel"], self._loads(write_row["value_type"], write_row["value_blob"]))
            for write_row in write_rows
        ]
        parent_checkpoint_id = row["parent_checkpoint_id"]
        return CheckpointTuple(
            config={
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": checkpoint_id,
                }
            },
            checkpoint=checkpoint_with_values,
            metadata=metadata,
            pending_writes=pending_writes,
            parent_config=(
                {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": parent_checkpoint_id,
                    }
                }
                if parent_checkpoint_id
                else None
            ),
        )

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = get_checkpoint_id(config)
        query = """
            SELECT *
            FROM checkpoints
            WHERE thread_id = ? AND checkpoint_ns = ?
        """
        params: list[Any] = [thread_id, checkpoint_ns]
        if checkpoint_id:
            query += " AND checkpoint_id = ?"
            params.append(checkpoint_id)
        query += " ORDER BY checkpoint_id DESC LIMIT 1"
        with self._lock:
            row = self._conn.execute(query, params).fetchone()
        return self._row_to_tuple(row) if row else None

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        clauses: list[str] = []
        params: list[Any] = []
        if config:
            clauses.append("thread_id = ?")
            params.append(config["configurable"]["thread_id"])
            if "checkpoint_ns" in config["configurable"]:
                clauses.append("checkpoint_ns = ?")
                params.append(config["configurable"]["checkpoint_ns"])
            if checkpoint_id := get_checkpoint_id(config):
                clauses.append("checkpoint_id = ?")
                params.append(checkpoint_id)
        if before and (before_id := get_checkpoint_id(before)):
            clauses.append("checkpoint_id < ?")
            params.append(before_id)
        query = "SELECT * FROM checkpoints"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY checkpoint_id DESC"
        if limit is not None:
            query += f" LIMIT {int(limit)}"
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        yielded = 0
        for row in rows:
            tuple_row = self._row_to_tuple(row)
            if filter and not all(tuple_row.metadata.get(key) == value for key, value in filter.items()):
                continue
            yield tuple_row
            yielded += 1
            if limit is not None and yielded >= limit:
                break

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = checkpoint["id"]
        checkpoint_copy = checkpoint.copy()
        values: dict[str, Any] = checkpoint_copy.pop("channel_values")
        checkpoint_type, checkpoint_blob = self.serde.dumps_typed(checkpoint_copy)
        metadata_type, metadata_blob = self.serde.dumps_typed(get_checkpoint_metadata(config, metadata))
        parent_checkpoint_id = config["configurable"].get("checkpoint_id")
        with self._lock, self._conn:
            for channel, version in new_versions.items():
                if channel in values:
                    value_type, value_blob = self.serde.dumps_typed(values[channel])
                else:
                    value_type, value_blob = ("empty", b"")
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO checkpoint_blobs
                    (thread_id, checkpoint_ns, channel, version, value_type, value_blob)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (thread_id, checkpoint_ns, channel, str(version), value_type, sqlite3.Binary(value_blob)),
                )
            self._conn.execute(
                """
                INSERT OR REPLACE INTO checkpoints
                (thread_id, checkpoint_ns, checkpoint_id, checkpoint_type, checkpoint_blob, metadata_type, metadata_blob, parent_checkpoint_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    thread_id,
                    checkpoint_ns,
                    checkpoint_id,
                    checkpoint_type,
                    sqlite3.Binary(checkpoint_blob),
                    metadata_type,
                    sqlite3.Binary(metadata_blob),
                    parent_checkpoint_id,
                    _encode_datetime(_utcnow()),
                ),
            )
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"]["checkpoint_id"]
        with self._lock, self._conn:
            for idx, (channel, value) in enumerate(writes):
                write_idx = WRITES_IDX_MAP.get(channel, idx)
                if write_idx < 0:
                    exists = self._conn.execute(
                        """
                        SELECT 1 FROM checkpoint_writes
                        WHERE thread_id = ? AND checkpoint_ns = ? AND checkpoint_id = ? AND task_id = ? AND idx = ?
                        """,
                        (thread_id, checkpoint_ns, checkpoint_id, task_id, write_idx),
                    ).fetchone()
                    if exists:
                        continue
                value_type, value_blob = self.serde.dumps_typed(value)
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO checkpoint_writes
                    (thread_id, checkpoint_ns, checkpoint_id, task_id, idx, channel, value_type, value_blob, task_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        thread_id,
                        checkpoint_ns,
                        checkpoint_id,
                        task_id,
                        write_idx,
                        channel,
                        value_type,
                        sqlite3.Binary(value_blob),
                        task_path,
                    ),
                )

    def delete_thread(self, thread_id: str) -> None:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
            self._conn.execute("DELETE FROM checkpoint_blobs WHERE thread_id = ?", (thread_id,))
            self._conn.execute("DELETE FROM checkpoint_writes WHERE thread_id = ?", (thread_id,))

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        return self.get_tuple(config)

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ):
        for item in self.list(config, filter=filter, before=before, limit=limit):
            yield item

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        return self.put(config, checkpoint, metadata, new_versions)

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        self.put_writes(config, writes, task_id, task_path)

    async def adelete_thread(self, thread_id: str) -> None:
        self.delete_thread(thread_id)

    def get_next_version(self, current: str | None, channel: None) -> str:
        if current is None:
            current_v = 0
        elif isinstance(current, int):
            current_v = current
        else:
            current_v = int(str(current).split(".")[0])
        return f"{current_v + 1:032}.{int(_utcnow().timestamp() * 1_000_000):016}"


class SqliteStore(BaseStore):
    """SQLite-backed key-value store for durable runtime memory."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS store_items (
                    namespace TEXT NOT NULL,
                    item_key TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (namespace, item_key)
                )
                """
            )

    def _match_namespace(self, namespace: tuple[str, ...], prefix: tuple[str, ...]) -> bool:
        return len(namespace) >= len(prefix) and namespace[: len(prefix)] == prefix

    def _match_filters(self, value: dict[str, Any], filter_spec: dict[str, Any] | None) -> bool:
        if not filter_spec:
            return True
        return all(value.get(key) == expected for key, expected in filter_spec.items())

    def _build_item(self, row: sqlite3.Row) -> Item:
        namespace = _decode_namespace(row["namespace"])
        value = json.loads(row["value_json"])
        return Item(
            namespace=namespace,
            key=row["item_key"],
            value=value,
            created_at=_decode_datetime(row["created_at"]),
            updated_at=_decode_datetime(row["updated_at"]),
        )

    def batch(self, ops: Iterable[Any]) -> list[Result]:
        results: list[Result] = []
        with self._lock, self._conn:
            for op in ops:
                if isinstance(op, GetOp):
                    row = self._conn.execute(
                        "SELECT * FROM store_items WHERE namespace = ? AND item_key = ?",
                        (_encode_namespace(op.namespace), op.key),
                    ).fetchone()
                    results.append(self._build_item(row) if row else None)
                    continue
                if isinstance(op, SearchOp):
                    rows = self._conn.execute("SELECT * FROM store_items ORDER BY updated_at DESC").fetchall()
                    items: list[SearchItem] = []
                    for row in rows:
                        item = self._build_item(row)
                        if not self._match_namespace(item.namespace, op.namespace_prefix):
                            continue
                        if not self._match_filters(item.value, op.filter):
                            continue
                        items.append(
                            SearchItem(
                                namespace=item.namespace,
                                key=item.key,
                                value=item.value,
                                created_at=item.created_at,
                                updated_at=item.updated_at,
                            )
                        )
                    results.append(items[op.offset : op.offset + op.limit])
                    continue
                if isinstance(op, ListNamespacesOp):
                    rows = self._conn.execute("SELECT DISTINCT namespace FROM store_items").fetchall()
                    namespaces = [_decode_namespace(row["namespace"]) for row in rows]
                    for condition in op.match_conditions:
                        if condition.match_type == "prefix":
                            namespaces = [ns for ns in namespaces if self._match_namespace(ns, condition.path)]
                        elif condition.match_type == "suffix":
                            namespaces = [ns for ns in namespaces if len(ns) >= len(condition.path) and ns[-len(condition.path) :] == condition.path]
                    if op.max_depth is not None:
                        namespaces = sorted({ns[: op.max_depth] for ns in namespaces})
                    else:
                        namespaces = sorted(set(namespaces))
                    results.append(namespaces[op.offset : op.offset + op.limit])
                    continue
                if isinstance(op, PutOp):
                    namespace = _encode_namespace(op.namespace)
                    if op.value is None:
                        self._conn.execute(
                            "DELETE FROM store_items WHERE namespace = ? AND item_key = ?",
                            (namespace, op.key),
                        )
                    else:
                        row = self._conn.execute(
                            "SELECT created_at FROM store_items WHERE namespace = ? AND item_key = ?",
                            (namespace, op.key),
                        ).fetchone()
                        created_at = row["created_at"] if row else _encode_datetime(_utcnow())
                        self._conn.execute(
                            """
                            INSERT OR REPLACE INTO store_items (namespace, item_key, value_json, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (
                                namespace,
                                op.key,
                                json.dumps(op.value, separators=(",", ":"), default=str),
                                created_at,
                                _encode_datetime(_utcnow()),
                            ),
                        )
                    results.append(None)
                    continue
                raise ValueError(f"Unknown operation type: {type(op)!r}")
        return results

    async def abatch(self, ops: Iterable[Any]) -> list[Result]:
        return self.batch(ops)


class SqliteRunCoordinator:
    """Shared run coordination with workspace and thread admission control."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        with self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS runtime_threads (
                    thread_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    assistant_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    active_run_id TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS runtime_runs (
                    run_id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    assistant_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    def acquire_run(
        self,
        *,
        assistant_id: str,
        thread_id: str,
        run_id: str,
        workspace_id: str,
        user_id: str,
        max_runs_per_workspace: int,
        max_runs_per_thread: int,
    ) -> None:
        with self._lock, self._conn:
            workspace_active = self._conn.execute(
                "SELECT COUNT(*) AS count FROM runtime_runs WHERE workspace_id = ? AND status = 'active'",
                (workspace_id,),
            ).fetchone()["count"]
            if workspace_active >= max_runs_per_workspace:
                raise RuntimeError("Workspace run cap reached.")

            thread_active = self._conn.execute(
                "SELECT COUNT(*) AS count FROM runtime_runs WHERE thread_id = ? AND status = 'active'",
                (thread_id,),
            ).fetchone()["count"]
            if thread_active >= max_runs_per_thread:
                raise RuntimeError("Another run is already active for this thread.")

            now = _encode_datetime(_utcnow())
            self._conn.execute(
                """
                INSERT OR REPLACE INTO runtime_threads
                (thread_id, workspace_id, user_id, assistant_id, status, active_run_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (thread_id, workspace_id, user_id, assistant_id, "busy", run_id, now),
            )
            self._conn.execute(
                """
                INSERT OR REPLACE INTO runtime_runs
                (run_id, thread_id, workspace_id, user_id, assistant_id, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
                """,
                (run_id, thread_id, workspace_id, user_id, assistant_id, now, now),
            )

    def complete_run(self, *, thread_id: str, run_id: str, status: str) -> None:
        with self._lock, self._conn:
            now = _encode_datetime(_utcnow())
            self._conn.execute(
                "UPDATE runtime_runs SET status = ?, updated_at = ? WHERE run_id = ?",
                (status, now, run_id),
            )
            active = self._conn.execute(
                "SELECT COUNT(*) AS count FROM runtime_runs WHERE thread_id = ? AND status = 'active'",
                (thread_id,),
            ).fetchone()["count"]
            thread_status = "busy" if active else ("interrupted" if status == "interrupted" else "idle")
            active_run_id = run_id if status == "interrupted" else None
            self._conn.execute(
                "UPDATE runtime_threads SET status = ?, active_run_id = ?, updated_at = ? WHERE thread_id = ?",
                (thread_status, active_run_id, now, thread_id),
            )

    def get_thread(self, thread_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM runtime_threads WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()
        return dict(row) if row else None
