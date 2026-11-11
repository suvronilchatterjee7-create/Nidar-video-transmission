"""Config-driven component registry.

Components are registered by name in ``registry.json`` with interface, module, class, platforms,
sources and evidence level. No hard-coded routing tables; unknown names and platform mismatches fail
loudly, naming the component. [ADIAT-inspired: algorithms.conf, CLAUDE.md §2.3]
The ``sources`` field feeds the traceability check (tests/traceability).
"""
from __future__ import annotations

import importlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

PLATFORMS = frozenset({"onboard", "gcs", "sim"})
EVIDENCE_LEVELS = frozenset({"PROVED", "REPRODUCED", "SIMULATED", "TARGET", "REQUIRED", "OPEN", "INFRA"})
DEFAULT_PATH = Path(__file__).with_name("registry.json")
SOURCE_TAG = re.compile(r"^(BRIEF|P1|P2|ADIAT-inspired|USER-PROMPT|DATASET)\b")


class RegistryError(ValueError):
    """Malformed registry file."""


class UnknownComponentError(KeyError):
    def __init__(self, name: str, known: Iterable[str]) -> None:
        super().__init__(f"unknown component {name!r}; registered: {sorted(known)}")


class PlatformMismatchError(RuntimeError):
    def __init__(self, name: str, platform: str, allowed: Iterable[str]) -> None:
        super().__init__(f"component {name!r} is not registered for platform {platform!r} (allowed: {sorted(allowed)})")


@dataclass(frozen=True)
class ComponentSpec:
    name: str
    interface: str
    module: str
    cls: str
    platforms: frozenset[str]
    sources: tuple[str, ...]
    evidence: str

    @staticmethod
    def from_json(entry: dict) -> "ComponentSpec":
        missing = {"name", "interface", "module", "class", "platforms", "sources", "evidence"} - set(entry)
        if missing:
            raise RegistryError(f"registry entry {entry.get('name', '?')!r} missing fields {sorted(missing)}")
        spec = ComponentSpec(
            name=entry["name"], interface=entry["interface"], module=entry["module"], cls=entry["class"],
            platforms=frozenset(entry["platforms"]), sources=tuple(entry["sources"]), evidence=entry["evidence"],
        )
        if not spec.platforms or not spec.platforms <= PLATFORMS:
            raise RegistryError(f"{spec.name}: platforms {sorted(spec.platforms)} must be a non-empty subset of "
                                f"{sorted(PLATFORMS)}")
        if not spec.sources or not all(SOURCE_TAG.match(s) for s in spec.sources):
            raise RegistryError(f"{spec.name}: every component needs >= 1 source tag "
                                "(BRIEF/P1/P2/ADIAT-inspired/USER-PROMPT/DATASET) [USER-PROMPT §0.2]")
        if spec.evidence.split()[0] not in EVIDENCE_LEVELS:
            raise RegistryError(f"{spec.name}: evidence must start with one of {sorted(EVIDENCE_LEVELS)}")
        return spec


class Registry:
    def __init__(self, specs: Iterable[ComponentSpec]) -> None:
        self._specs: dict[str, ComponentSpec] = {}
        for s in specs:
            if s.name in self._specs:
                raise RegistryError(f"duplicate component name {s.name!r}")
            self._specs[s.name] = s

    @classmethod
    def load(cls, path: Path | str | None = None) -> "Registry":
        p = Path(path) if path is not None else DEFAULT_PATH
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RegistryError(f"cannot read registry {p}: {exc}") from exc
        return cls(ComponentSpec.from_json(e) for e in data.get("components", []))

    def names(self) -> list[str]:
        return sorted(self._specs)

    def spec(self, name: str) -> ComponentSpec:
        if name not in self._specs:
            raise UnknownComponentError(name, self._specs)
        return self._specs[name]

    def resolve(self, name: str, platform: str) -> type:
        """Import and return the class registered under ``name`` for ``platform``."""
        s = self.spec(name)
        if platform not in s.platforms:
            raise PlatformMismatchError(name, platform, s.platforms)
        module = importlib.import_module(s.module)
        try:
            return getattr(module, s.cls)
        except AttributeError as exc:
            raise RegistryError(f"{name}: module {s.module} has no class {s.cls}") from exc
