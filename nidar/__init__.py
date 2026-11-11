"""NIDAR RescueSwarm runtime package.

Layers (docs/ARCHITECTURE.md §3): ``common`` (contracts, units, registry, logging),
``onboard`` (per-drone autonomy, [P2 §1-§14]), ``swarm`` (multi-agent logic, [P2 §5, §7, §9.3]),
``link`` (local RF only, [BRIEF §5] [P2 §12.1] [P1 §3.1]), ``video`` (Paper 1, [P1]),
``gcs`` (single operator station, [BRIEF §4]).

Phase 2 status: contracts and infrastructure are implemented; algorithm modules are stubs that
raise :class:`nidar.common.stub.NotYetImplemented` and cite the equations they will implement.
"""

__version__ = "0.2.0"
