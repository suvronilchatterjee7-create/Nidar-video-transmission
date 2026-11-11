"""CT-12 controller output always in the certified grid [P1 Prop. 18]; CT-14 channel simulator statistics
[P1 §6.1, A7]; quality helpers [P1 Prop. 10]."""
from __future__ import annotations

import math

import numpy as np
import pytest

from nidar.common.contracts import CertifiedFloorDesign, SnrReport
from nidar.video.certificates.grid import CertifiedGrid
from nidar.video.control.controller import DampedFloorController
from nidar.video.control.snr_predictor import KalmanSnrPredictor, prediction_variance
from nidar.video.quality import beta_up
from sim.channel.block_fading import block_gains
from sim.channel.snr_process import simulate


def _design(gdb: float, n_f: int) -> CertifiedFloorDesign:
    return CertifiedFloorDesign(f"d{gdb}", gdb, n_f, 4, n_f // 4, 1000, 1e-3, 3.0, 4e-4, 10**6, 1e-6)


def test_ct12_controller_output_always_in_grid() -> None:
    grid = CertifiedGrid([_design(g, n) for g, n in ((6.0, 4000), (8.0, 3200), (10.0, 2800), (12.0, 2400))])
    rng = np.random.default_rng(0)

    def wild_map(g: float) -> float:          # deliberately divergent / random map: safety must not depend on it
        return float(rng.uniform(-20, 40))

    ctl = DampedFloorController({10.0: grid}, wild_map, beta=1.7, gamma0_db=9.0)
    members = set(id(d) for d in grid.designs)
    for _ in range(500):
        out = ctl.step(design_snr_db=10.0, n_available=3500)
        assert out is None or (id(out) in members and out.n_f <= 3500 and out.gamma_f_db >= ctl.gamma_db)
    assert ctl.step(design_snr_db=5.0, n_available=3500) is None      # no grid certified at <= 5 dB


def test_grid_round_trip(tmp_path) -> None:
    grid = CertifiedGrid([_design(8.0, 3200), _design(10.0, 2800)])
    path = tmp_path / "grid.json"
    grid.save(str(path))
    loaded = CertifiedGrid()
    loaded.load(str(path))
    assert loaded.designs == grid.designs
    assert loaded.nearest_not_below(9.0, 10_000).gamma_f_db == 10.0
    assert loaded.nearest_not_below(11.0, 10_000) is None


def test_ct14_block_gain_statistics() -> None:
    g = block_gains(8, 100_000, seed=1)
    assert g.mean() == pytest.approx(1.0, abs=0.01)
    assert g.var() == pytest.approx(1.0, abs=0.03)                    # Exp(1)
    gc = block_gains(2, 200_000, seed=2, corr=0.9)
    assert gc.mean() == pytest.approx(1.0, abs=0.02)
    assert np.corrcoef(gc[1:, 0], gc[:-1, 0])[0, 1] == pytest.approx(0.81, abs=0.01)   # |corr|^2


def test_ct14_snr_process_statistics() -> None:
    s, rep = simulate(200_000, 15.0, 0.875, 3.0, 1.0, delay=2, seed=4)
    assert s.mean() == pytest.approx(15.0, abs=0.1) and s.std() == pytest.approx(3.0, abs=0.05)
    assert np.corrcoef(s[1:], s[:-1])[0, 1] == pytest.approx(0.875, abs=0.01)
    assert np.isnan(rep[:2]).all()
    assert np.std(rep[2:] - s[:-2]) == pytest.approx(1.0, abs=0.02)


def test_predictor_converges_to_lemma8_variance() -> None:
    p = KalmanSnrPredictor(15.0, 0.875, 3.0, 1.0, delay=1)
    for g in range(200):
        p.update(SnrReport(1, 1, g, 0.0, 15.0, 1))
    _, var = p.predicted()
    assert var == pytest.approx(prediction_variance(1, 0.875, 3.0, 1.0), rel=1e-9)


def test_beta_up() -> None:
    assert beta_up(np.array([1.0, 1.0, 2.0]), np.array([False, True, True])) == pytest.approx(0.75)
    with pytest.raises(ValueError):
        beta_up(np.zeros(2), np.ones(2, bool))
    assert math.isfinite(beta_up(np.array([1.0]), np.array([False])))
