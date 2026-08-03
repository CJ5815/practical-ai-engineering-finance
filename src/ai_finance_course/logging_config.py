"""Structured logging configuration for the API.

Deliberately plain: Python's built-in logging module, one format string,
no extra dependency. A deployed service needs its logs to go somewhere
predictable (stdout, so a container runtime or log collector can pick
them up) with enough structure to grep — timestamp, level, logger name,
message. That's the whole requirement; nothing here needs structlog or a
JSON formatter to meet it.
"""

from __future__ import annotations

import logging


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once, at process startup.

    Args:
        level: A standard logging level name (e.g. "INFO", "DEBUG").
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
