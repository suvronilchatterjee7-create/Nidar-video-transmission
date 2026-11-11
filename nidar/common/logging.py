"""Central logging service.

Production paths log through here, never ``print`` (ruff T20 gate). Errors carry context: which
component, which operation, which input (drone id, GoP index, file) failed.
[ADIAT-inspired: LoggerService; CLAUDE.md §2.4]
"""
from __future__ import annotations

import logging
from typing import Any, Mapping

ROOT_LOGGER_NAME = "nidar"


def get_logger(component: str) -> logging.Logger:
    """Logger for a component, namespaced under ``nidar.`` (e.g. ``nidar.video.decoder``)."""
    name = component if component.startswith(ROOT_LOGGER_NAME) else f"{ROOT_LOGGER_NAME}.{component}"
    return logging.getLogger(name)


def configure(level: int = logging.INFO) -> None:
    """Idempotent console configuration for tools and simulators (runtime nodes may add handlers)."""
    root = logging.getLogger(ROOT_LOGGER_NAME)
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(handler)
    root.setLevel(level)


class ContextError(RuntimeError):
    """Error that names component, operation and input. Message is self-describing."""

    def __init__(self, component: str, operation: str, inputs: Mapping[str, Any] | None = None,
                 cause: BaseException | None = None) -> None:
        self.component = component
        self.operation = operation
        self.inputs = dict(inputs or {})
        self.cause = cause
        detail = ", ".join(f"{k}={v!r}" for k, v in self.inputs.items())
        reason = f": {type(cause).__name__}: {cause}" if cause is not None else ""
        super().__init__(f"[{component}] {operation} failed ({detail}){reason}")
