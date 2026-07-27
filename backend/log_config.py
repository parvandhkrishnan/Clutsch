"""Structured JSON logging with request ID propagation for Clutsch."""
import logging
import json
import uuid
import sys
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """Format log records as JSON with a consistent schema."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Add request_id if present (set via LogContext)
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "latency_ms"):
            log_entry["latency_ms"] = record.latency_ms
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, default=str)


def setup_logging():
    """Configure the root logger to emit JSON lines."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


class LogContext:
    """Context manager to attach request_id (and other fields) to all log records within a scope."""

    _request_id = None

    @classmethod
    def get_request_id(cls) -> str:
        return cls._request_id or ""

    @classmethod
    def set_request_id(cls, rid: str):
        cls._request_id = rid

    @classmethod
    def clear(cls):
        cls._request_id = None