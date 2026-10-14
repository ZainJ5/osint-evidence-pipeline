"""Project exception hierarchy. Adapters translate vendor exceptions into these."""


class PipelineError(Exception):
    """Base error. Carries a stable error code and a context dict for structured logs."""

    code = "PIPELINE_ERROR"

    def __init__(self, message: str, code: str | None = None, context: dict | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.context = context or {}


class ValidationError(PipelineError):
    """Invalid input or configuration."""

    code = "VALIDATION_ERROR"


class CollectionError(PipelineError):
    """Fetching a public profile failed (M1)."""

    code = "COLLECTION_ERROR"


class SnapshotError(PipelineError):
    """Storing or loading a raw snapshot failed (M2)."""

    code = "SNAPSHOT_ERROR"


class ExtractionError(PipelineError):
    """Parsing a snapshot into evidence failed (M2)."""

    code = "EXTRACTION_ERROR"


class ResolutionError(PipelineError):
    """Identity resolution failed (M3)."""

    code = "RESOLUTION_ERROR"


class MatchingError(PipelineError):
    """Requirement matching failed (M4)."""

    code = "MATCHING_ERROR"


class ScoringError(PipelineError):
    """Claim verification or scoring failed (M5)."""

    code = "SCORING_ERROR"
