"""Priority multiplexing of telemetry classes: state > map > video [P2 §12.1 / §15.1.1].

Paper 2 writes this as a linear programme with weights 10 / 5 / 1 and only a total-rate constraint, which
gives everything to the top class (OQ-15). What it describes in words is a priority order, so this
scheduler is strict priority: classes are served in descending weight until the capacity is used; inside a
class, items go in arrival order. Optional per-class caps (no default) keep a class from starving the rest.
"""
from __future__ import annotations

PAPER_WEIGHTS = {"state": 10, "map": 5, "video": 1}      # [P2 §12.1]


class PriorityMux:
    def __init__(self, weights: dict | None = None, caps: dict | None = None) -> None:
        self.weights = dict(PAPER_WEIGHTS if weights is None else weights)
        self.caps = dict(caps or {})

    def schedule(self, queues: dict, capacity: int) -> dict:
        """``queues``: class -> list of item sizes. Returns class -> number of items sent this round."""
        unknown = set(queues) - set(self.weights)
        if unknown:
            raise ValueError(f"unknown traffic class(es) {sorted(unknown)}; known: {sorted(self.weights)}")
        sent = {name: 0 for name in queues}
        left = capacity
        for name in sorted(queues, key=lambda k: -self.weights[k]):
            budget = min(left, self.caps.get(name, left))
            for size in queues[name]:
                if size > budget:
                    break
                budget -= size
                left -= size
                sent[name] += 1
        return sent
