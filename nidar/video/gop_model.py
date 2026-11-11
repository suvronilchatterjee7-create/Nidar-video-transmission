"""Per-GoP design shared by encoder and decoder: water level, coded set, quantiser steps, refinement gains.

Everything here is a deterministic function of the CURRENT GoP's protected metadata, the configuration and
n_F, so encoder and decoder compute identical gains without sending them and without any dependence on an
earlier GoP (the gains stay as firewalled as the floor) [P1 Rem. 6 "open loop", A5].
The model side information uses the steady state of the scalar Kalman recursion (Eq. 9 + Prop. 3) iterated
jointly with Prop. 8: mu = omega + a^2 D, kappa from Eq. 18, D from the allocation, repeated to a fixed
point, at chunk level (all coefficients of a chunk share lambda, omega, a). The decoder's *actual* side
information (Lemma 9) is used only in the conditional mean, never in the gains.
Active-set limit: M = 2 n_A real dimensions [P1 Rem. 6] (block-Hadamard spreading needs no padding).
These are implementation choices,
recorded in docs/VIDEO_PIPELINE.md §3.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from nidar.video.config import VideoLinkConfig
from nidar.video.decoder import posterior_after_floor, transmitted_variance
from nidar.video.floor import quantiser
from nidar.video.floor.designer import water_level
from nidar.video.refinement import allocator, limiter
from nidar.video.variance_field import ChunkLayout

MODEL_ITERATIONS = 8


@dataclass(frozen=True)
class GopDesign:
    theta_f: float
    lam: np.ndarray            # per coefficient
    omega: np.ndarray
    a: np.ndarray
    coded: np.ndarray          # bool, i in F
    steps_chunk: np.ndarray    # quantiser step per chunk (inf if not coded)
    n_floor: int
    n_analog: int
    x: np.ndarray              # g_i^2 per coefficient (0 if inactive)
    active: np.ndarray         # bool per coefficient
    nu_model: float            # per real dimension, open-loop
    analog_energy: float
    alpha: float               # limiter Bussgang gain (1 if no limiter)
    clip_dist: float           # sigma_d^2 / sigma^2 (0 if no limiter)
    model_d_chunk: np.ndarray  # model distortion per chunk (open loop)

    @property
    def active_index(self) -> np.ndarray:
        return np.flatnonzero(self.active)


def water_level_for(cfg: VideoLinkConfig, layout: ChunkLayout, lam: np.ndarray, omega: np.ndarray,
                    a: np.ndarray) -> float:
    """theta_F with R_ref = credited bits [P1 Def. 7], computed per chunk with counts."""
    credited_bits = cfg.credited_bits_per_sample * cfg.samples_per_gop()
    return water_level(lam, omega, a, credited_bits / cfg.t_g, cfg.t_g, counts=layout.counts)


def max_active_dims(n_analog: int, spreading: str) -> int:
    """M = 2 n_A [P1 Rem. 6]; the spreader keeps the exact length for every family."""
    return 2 * n_analog


def design(cfg: VideoLinkConfig, layout: ChunkLayout, lam_c: np.ndarray, omega_c: np.ndarray, a_c: np.ndarray,
           theta_f: float, n_floor: int) -> GopDesign:
    n_total = cfg.channel_uses()
    n_pilot = cfg.fading_blocks * cfg.pilots_per_block
    n_analog = n_total - cfg.n_telemetry - n_pilot - n_floor
    lab = layout.flat_labels()
    lam, omega, a = lam_c[lab], omega_c[lab], a_c[lab]
    coded = lam > theta_f
    steps_chunk = quantiser.step_sizes(lam_c, theta_f)
    vartheta_c = transmitted_variance(lam_c, theta_f)
    d_c = np.minimum(lam_c, theta_f)
    if n_analog <= 0:
        z = np.zeros_like(lam)
        return GopDesign(theta_f, lam, omega, a, coded, steps_chunk, n_floor, max(n_analog, 0), z, z.astype(bool),
                         0.0, 0.0, 1.0, 0.0, d_c)
    analog_energy = max((n_floor + n_analog) * 1.0 - n_floor * cfg.floor_power_ratio, 0.0)   # [P1 §6.5]
    nu_c = 10.0 ** (-cfg.expected_snr_db / 10.0)
    alpha, dist = 1.0, 0.0
    nu = nu_c / 2.0
    if cfg.limiter_backoff_db is not None:                    # [P1 §B.1 effective noise]
        alpha, dist = limiter.bussgang(10.0 ** (cfg.limiter_backoff_db / 10.0))
        nu = (nu_c / 2.0 + dist * analog_energy / (2.0 * n_analog)) / alpha**2
    m_dims = max_active_dims(n_analog, cfg.spreading)
    counts = layout.counts.astype(float)
    nu_c_arr = np.full(lam_c.shape, nu)
    al, n_act = None, None
    for _ in range(MODEL_ITERATIONS):
        mu_c = omega_c + a_c * a_c * d_c
        kappa_c = posterior_after_floor(mu_c, theta_f, lam_c)
        al, n_act = allocator.allocate_grouped(kappa_c, vartheta_c, nu_c_arr, counts, analog_energy, m_dims)
        d_c = (n_act * al.d + (counts - n_act) * kappa_c) / counts
    active = layout.rank_in_chunk() < np.rint(n_act).astype(np.int64)[lab]
    x = np.where(active, al.x[lab], 0.0)
    return GopDesign(theta_f, lam, omega, a, coded, steps_chunk, n_floor, n_analog, x, active, nu,
                     analog_energy, alpha, dist, d_c)
