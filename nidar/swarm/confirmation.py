"""Bayesian survivor confirmation: prior 0.01, CNN-confidence update, K consistent frames, promote at
P > 0.95 [P2 §9.3 Eq. 258-265].

Update per detection: P <- C P / (C P + (1 - C)(1 - P)) with C the CNN confidence [P2 Eq. 260]. A candidate
is promoted once it has K >= K_min associated observations [Eq. 261-262] and P > theta_confirm [Eq. 264-265].
Observations flagged low-confidence (covariance gate, [P2 Eq. 100]) are not used.

Choices the paper leaves open, made explicit here: observations are associated to a candidate within r_tol
[Eq. 263]; a gap longer than ``max_gap_s`` resets the frame count ("spatially consistent over K consecutive
observations"); positions are fused by inverse-covariance weighting; ``r_tol_m`` and ``max_gap_s`` have no
default. The update treats every frame as independent evidence, exactly as the paper writes it: confidence
calibration and frame correlation are OQ-25 / IDEA-09.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from nidar.common.contracts import SCHEMA_VERSION, GeotagObservation, SurvivorStatus, SurvivorTrack


def bayes_update(p: float, confidence: float) -> float:
    """[P2 Eq. 260]"""
    return confidence * p / (confidence * p + (1.0 - confidence) * (1.0 - p))


@dataclass
class _Candidate:
    track_id: str
    info: np.ndarray                 # sum of inverse covariances
    info_mean: np.ndarray            # sum of inverse covariance x position
    belief: float
    frames: int
    drones: set = field(default_factory=set)
    t_first: float = 0.0
    t_last: float = 0.0
    confirmed: bool = False
    suppressed: bool = False         # already confirmed elsewhere (merge_remote)

    @property
    def position(self) -> np.ndarray:
        return np.linalg.solve(self.info, self.info_mean)

    @property
    def covariance(self) -> np.ndarray:
        return np.linalg.inv(self.info)


class BayesianConfirmer:
    """Implements ``SurvivorConfirmer`` (docs/INTERFACES.md §9)."""

    def __init__(self, r_tol_m: float, max_gap_s: float, id_prefix: str, prior: float = 0.01, k_min: int = 10,
                 confirm_threshold: float = 0.95) -> None:
        # prior, k_min, confirm_threshold default to the paper's proposed values [P2 Eq. 259, 262, 265]
        self.r_tol_m, self.max_gap_s, self.id_prefix = r_tol_m, max_gap_s, id_prefix
        self.prior, self.k_min, self.confirm_threshold = prior, k_min, confirm_threshold
        self.candidates: list[_Candidate] = []
        self._next = 0

    def _nearest(self, p: np.ndarray) -> _Candidate | None:
        best, best_d = None, self.r_tol_m
        for c in self.candidates:
            d = float(np.linalg.norm(c.position[:2] - p[:2]))
            if d <= best_d:
                best, best_d = c, d
        return best

    def _track(self, c: _Candidate, status: str, t_confirmed: float | None) -> SurvivorTrack:
        return SurvivorTrack(SCHEMA_VERSION, c.track_id, c.position, c.covariance, c.belief, c.frames,
                             frozenset(c.drones), status, c.t_first, t_confirmed)

    def observe(self, obs: GeotagObservation) -> SurvivorTrack | None:
        """Feed one geotagged detection; returns the track once, at the moment it is promoted."""
        if obs.low_confidence:
            return None
        t = obs.detection.t_source
        w = np.linalg.inv(obs.sigma_surv)
        c = self._nearest(obs.p_surv)
        if c is None:
            c = _Candidate(f"{self.id_prefix}-{self._next}", np.zeros((3, 3)), np.zeros(3), self.prior, 0, set(), t, t)
            self._next += 1
            self.candidates.append(c)
        elif t - c.t_last > self.max_gap_s:
            c.frames = 0                                   # consistency broken [P2 Eq. 261]
        c.info = c.info + w
        c.info_mean = c.info_mean + w @ obs.p_surv
        c.belief = bayes_update(c.belief, obs.detection.confidence)
        c.frames += 1
        c.drones.add(obs.detection.drone_id)
        c.t_last = t
        if (not c.confirmed and not c.suppressed and c.frames >= self.k_min
                and c.belief > self.confirm_threshold):
            c.confirmed = True
            return self._track(c, SurvivorStatus.CONFIRMED, t)
        return None

    def merge_remote(self, track: SurvivorTrack) -> None:
        """A survivor confirmed elsewhere: never promote a local candidate within r_tol again [P2 Eq. 263]."""
        c = self._nearest(track.p_surv)
        if c is None:
            w = np.linalg.inv(track.sigma_surv)
            c = _Candidate(track.survivor_id, w, w @ track.p_surv, track.belief, track.consistent_frames,
                           set(track.observing_drones), track.t_first_seen, track.t_first_seen)
            self.candidates.append(c)
        c.suppressed = True

    def candidate_tracks(self) -> list[SurvivorTrack]:
        """Unconfirmed hypotheses (for a GCS that chooses to show provisional tags, OQ-05l)."""
        return [self._track(c, SurvivorStatus.CANDIDATE, None) for c in self.candidates
                if not c.confirmed and not c.suppressed]
