"""Domain errors — custom exception hierarchy."""


class DataFabricError(Exception):
    """Base error for the data-fabric domain."""

    def __init__(self, message: str, code: str = "DATA_FABRIC_ERROR") -> None:
        super().__init__(message)
        self.code = code


class IngestionError(DataFabricError):
    """Failed to ingest data from external source."""

    def __init__(self, source: str, reason: str) -> None:
        super().__init__(f"Ingestion failed for {source}: {reason}", code="INGESTION_ERROR")
        self.source = source


class ValidationError(DataFabricError):
    """Data quality validation failure."""

    def __init__(self, field: str, reason: str) -> None:
        super().__init__(f"Validation failed for {field}: {reason}", code="VALIDATION_ERROR")


class EntityNotFoundError(DataFabricError):
    """Requested entity does not exist."""

    def __init__(self, entity_type: str, identifier: str) -> None:
        super().__init__(f"{entity_type} '{identifier}' not found", code="NOT_FOUND")
