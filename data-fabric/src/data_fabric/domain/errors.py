"""Domain errors — business rule violations.

These are pure domain exceptions. They NEVER leak infrastructure concerns.
The API layer maps these to HTTP status codes.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base domain error."""
    pass


class EntityNotFoundError(DomainError):
    """Raised when a requested entity does not exist."""

    def __init__(self, entity_type: str, identifier: str) -> None:
        self.entity_type = entity_type
        self.identifier = identifier
        super().__init__(f"{entity_type} '{identifier}' not found")


class ValidationError(DomainError):
    """Raised when domain validation rules are violated."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        super().__init__(f"Validation error on '{field}': {message}")


class DataIngestionError(DomainError):
    """Raised when data ingestion fails."""

    def __init__(self, source: str, reason: str) -> None:
        self.source = source
        super().__init__(f"Ingestion from '{source}' failed: {reason}")


class SnapshotPendingError(DomainError):
    """Raised when an entity has no internal snapshot yet and a refresh was enqueued."""

    def __init__(
        self,
        entity_type: str,
        identifier: str,
        suggested_retry_seconds: int = 30,
    ) -> None:
        self.entity_type = entity_type
        self.identifier = identifier
        self.suggested_retry_seconds = suggested_retry_seconds
        super().__init__(
            f"{entity_type} '{identifier}' is pending refresh; retry in {suggested_retry_seconds}s"
        )
