"""Structured JSON logging. Email addresses are scrubbed before any output (NFR-06, QR-13)."""

import json
import logging
import re

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _scrub(value):
    if isinstance(value, str):
        return EMAIL_RE.sub("[email]", value)
    if isinstance(value, dict):
        return {k: _scrub(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_scrub(v) for v in value]
    return value


class EmailScrubFilter(logging.Filter):
    """Logging filter that masks email addresses in messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _scrub(record.getMessage())
        record.args = None
        if hasattr(record, "fields"):
            record.fields = _scrub(record.fields)
        return True


class JsonFormatter(logging.Formatter):
    """Formats log records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        data = {"level": record.levelname, "logger": record.name, "event": record.getMessage()}
        data.update(getattr(record, "fields", {}))
        return json.dumps(data, default=str)


def log_event(logger: logging.Logger, event: str, level: int = logging.INFO, **fields) -> None:
    """One log line per stage transition or error, e.g. log_event(log, "stage_done", run_id=..., stage=...)."""
    logger.log(level, event, extra={"fields": fields})


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(EmailScrubFilter())
    root = logging.getLogger("pipeline")
    root.handlers = [handler]
    root.setLevel(level)
