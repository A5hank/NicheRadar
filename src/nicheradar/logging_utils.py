"""Structured application logging that intentionally excludes secrets."""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


class JsonLogFormatter(logging.Formatter):
    """Render a conservative subset of log data as one JSON object."""

    _allowed_extra_fields = {
        "event",
        "endpoint",
        "status_code",
        "duration_ms",
        "request_id",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format safe metadata without serializing exception or request payloads."""

        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for field_name in self._allowed_extra_fields:
            value = getattr(record, field_name, None)

            if value is not None:
                payload[field_name] = value

        return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def configure_structured_logging() -> None:
    """Configure one application logger without changing host-level loggers."""

    logger = logging.getLogger("nicheradar")

    if logger.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
