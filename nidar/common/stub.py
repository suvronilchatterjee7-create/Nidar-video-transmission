"""Marker for Phase 2 stubs.

Every algorithm stub raises :class:`NotYetImplemented` naming the component, the source it will
implement, and the phase/approval it waits for, so a stub can never be mistaken for a result.
[USER-PROMPT §8 Phase 2 "empty module stubs with docstrings citing paper equations"]
"""
from __future__ import annotations


class NotYetImplemented(NotImplementedError):
    """Raised by every Phase 2 stub."""

    def __init__(self, component: str, source: str, waits_for: str = "approval of a later phase") -> None:
        self.component = component
        self.source = source
        self.waits_for = waits_for
        super().__init__(f"{component} is a stub (implements {source}); waits for {waits_for}")


def stub(component: str, source: str, waits_for: str = "approval of a later phase") -> NotYetImplemented:
    """Build the exception; use as ``raise stub(...)``."""
    return NotYetImplemented(component, source, waits_for)
