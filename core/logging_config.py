"""
Industrial Multi-Agent Ecosystem — Structured JSON Logging.

Configures the Python standard logging library to output structured
JSON logs to the terminal.
"""

from __future__ import annotations

import datetime
import json
import logging
import logging.config
import traceback
from typing import Any


class JSONFormatter(logging.Formatter):
    """
    Custom log formatter that outputs each log record as a single JSON line.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON string."""
        log_entry: dict[str, Any] = {
            "timestamp": datetime.datetime.fromtimestamp(
                record.created, tz=datetime.timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Merge extra fields passed via `extra={}` in logging calls
        reserved_attrs = {
            "name", "msg", "args", "created", "relativeCreated",
            "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "filename", "module", "pathname", "thread", "threadName",
            "process", "processName", "levelname", "levelno", "message",
            "msecs", "taskName",
        }
        for key, value in record.__dict__.items():
            if key not in reserved_attrs and not key.startswith("_"):
                log_entry[key] = value

        # Attach exception traceback if present
        if record.exc_info and record.exc_info[2] is not None:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else "Unknown",
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        return json.dumps(log_entry, ensure_ascii=False, default=str)


def setup_logging(log_level: str = "INFO") -> None:
    """Configure application-wide structured JSON logging."""
    config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JSONFormatter,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "level": log_level.upper(),
            "handlers": ["console"],
        },
        "loggers": {
            "uvicorn": {
                "level": log_level.upper(),
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn.error": {
                "level": log_level.upper(),
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": log_level.upper(),
                "handlers": ["console"],
                "propagate": False,
            },
            # Suppress noisy third-party loggers
            "httpx": {"level": "WARNING"},
            "httpcore": {"level": "WARNING"},
            "sentence_transformers": {"level": "WARNING"},
        },
    }
    logging.config.dictConfig(config)
