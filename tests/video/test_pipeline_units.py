"""Unit tests for the Paper 1 signal pipeline: transform (CT-10), metadata (CT-11), quantiser, entropy coder,
CRC, spreader, shared GoP design. [P1 Def. 4, Lemma 2, §D.3, §5.1 E4, E7, Rem. 7]"""
from __future__ import annotations

import numpy as np
import pytest

from nidar.video import gop_model, transform, variance_field
from nidar.video.config import paper_pilot_profile
from nidar.video.floor import code, crc, entropy, quantiser
from nidar.video.refinement import spreader


@pytest.mark.parametrize("kind", ["haar", "dct2"])
def test_ct10_transform_orthonormal_and_distortion_invariant(kind) -> None:
    rng = np.random.default_rng(0)
    x = rng.normal(size=(8, 32, 48))
    c = transform.forward(x, kind)
    assert np.allclose(transform.inverse(c, kind), x, atol=1e-12)
    assert np.sum(c * c) == pytest.approx(np.sum(x * x), rel=1e-12)           # Parseval
    e = rng.normal(scale=0.1, size=x.shape)
    assert np.sum((transform.forward(x + e, kind) - c) ** 2) == pytest.approx(np.sum(e * e), rel=1e-12)  # Lemma 2
    m = transform.temporal_matrix(8, kind)
    assert np.allclose(m @ m.T, np.eye(8), atol=1e-12)


def test_ct10_zones_and_haar_length() -> None:
    assert set(np.unique(transform.zone_map(16, 16))) == set(range(15))      # 15 zones [P1 Table 21]
    with pytest.raises(ValueError):
        transform.haar_matrix(6)


def test_ct11_pilot_layout_reproduces_paper_metadata_size() -> None:
    """640x352, G = 8, 4x4 luma / 2x2 chroma regions: 2,880 chunks and 36,360 metadata bits [P1 §D.3, Table 21]."""
    lay = variance_field.ChunkLayout.build(8, (352, 640), 4)
    assert lay.n_chunks == 2880
    meta = variance_field.quantise_metadata(np.ones(2880), np.ones(2880), np.zeros(2880), lay.is_dc)
    assert variance_field.metadata_bits(meta, lay.is_dc) == 36_360


def test_ct11_metadata_quantisation_round_trip() -> None:
    lay = variance_field.ChunkLayout.build(8, (32, 32), 1)
    rng = np.random.default_rng(1)
    lam = 10 ** rng.uniform(-4, 2, lay.n_chunks)
    lam[:3] = 1e-9                                          # negligible chunks
    omega = lam * rng.uniform(0.1, 1, lay.n_chunks)
    a = np.where(lay.is_dc, rng.uniform(0, 0.99, lay.n_chunks), 0)
    meta = variance_field.quantise_metadata(lam, omega, a, lay.is_dc)
    blob = variance_field.pack_metadata(meta, lay.is_dc)
    back, used = variance_field.unpack_metadata(blob, lay.n_chunks, lay.is_dc)
    assert used == len(blob) and np.array_equal(back.lam_db_q, meta.lam_db_q) and np.array_equal(back.a_q, meta.a_q)
    lq, oq, aq = variance_field.dequantise_metadata(back)
    in_range = lam > 10 ** (-4.15)
    assert np.all(np.abs(10 * np.log10(lq[in_range] / lam[in_range])) <= 0.5 + 1e-9)    # 1 dB steps
    assert np.all(lq[:3] == variance_field.NEGLIGIBLE)
    assert np.all(oq <= lq) and np.all(np.abs(aq - a) <= 0.5 / 32 + 1e-12)


def test_quantiser_meets_floor_target_at_high_resolution() -> None:
    """A6: coded coefficients reach D ~ theta_F with the test-channel step [P1 §5.2, Prop. 9]."""
    rng = np.random.default_rng(2)
    lam, theta = 100.0, 1.0
    c = rng.laplace(0, np.sqrt(lam / 2), 200_000)
    step = quantiser.step_sizes(np.array([lam]), theta)[0]
    est = quantiser.floor_estimate(quantiser.dequantise(quantiser.quantise(c, step), step), lam, theta)
    assert np.mean((c - est) ** 2) == pytest.approx(theta, rel=0.02)
    assert np.isinf(quantiser.step_sizes(np.array([0.5]), theta)[0])            # not coded


def test_entropy_coder_round_trip_with_escapes() -> None:
    rng = np.random.default_rng(3)
    lam = np.array([100.0, 4.0, 1.5])
    steps = quantiser.step_sizes(lam, 1.0)
    ids = rng.integers(0, 3, 5000)
    idx = quantiser.quantise(rng.laplace(0, np.sqrt(lam[ids] / 2)), steps[ids])
    idx[[10, 20, 30]] = [700, -450, 3000]
    data = entropy.encode(idx, ids, lam, steps)
    assert np.array_equal(entropy.decode(data, ids, lam, steps), idx)
    assert 8 * len(data) <= entropy.model_code_length_bits(idx, ids, lam, steps) + 200


def test_crc_detects_corruption() -> None:
    for r in (16, 32):
        block = crc.append_crc(b"floor payload", r)
        assert crc.check_crc(block, r) == (True, b"floor payload")
        bad = bytes([block[0] ^ 1]) + block[1:]
        assert crc.check_crc(bad, r)[0] is False


@pytest.mark.parametrize("family", ["identity", "hadamard"])
@pytest.mark.parametrize("n", [1, 7, 64, 1000])
def test_spreader_orthogonal_exact_length(family, n) -> None:
    rng = np.random.default_rng(n)
    v = rng.normal(size=n)
    s = spreader.spread(v, family)
    assert s.size == n and np.sum(s * s) == pytest.approx(np.sum(v * v))
    assert np.allclose(spreader.despread(s, family, n), v)
    nu = rng.uniform(0.1, 1, n)
    out = spreader.despread_noise(nu, family, n)
    assert out.sum() == pytest.approx(nu.sum())                                  # trace preserved


def test_complex_mapping_round_trip() -> None:
    r = np.arange(7.0)
    assert np.allclose(spreader.to_real(spreader.to_complex(r), 7), r)


def test_ideal_outage_code() -> None:
    c = code.IdealOutageFloorCode(2.0)
    assert c.uses_for(1001) == 501
    assert c.delivered(1000, np.full(500, 3.0)) and not c.delivered(1000, np.full(400, 3.0))


def test_gop_design_is_deterministic_and_within_budget() -> None:
    cfg = paper_pilot_profile((176, 320), snr_db=10)
    lay = variance_field.ChunkLayout.build(cfg.G, cfg.luma_hw, cfg.regions_luma)
    rng = np.random.default_rng(4)
    lam = 10 ** rng.uniform(-5, 1, lay.n_chunks)
    omega = lam * 0.3
    a = np.where(lay.is_dc, 0.8, 0.0)
    theta = gop_model.water_level_for(cfg, lay, lam, omega, a)
    d1 = gop_model.design(cfg, lay, lam, omega, a, theta, 30_000)
    d2 = gop_model.design(cfg, lay, lam, omega, a, theta, 30_000)
    assert np.array_equal(d1.x, d2.x) and np.array_equal(d1.active, d2.active)    # encoder == decoder
    assert d1.active.sum() <= 2 * d1.n_analog                                        # [P1 Rem. 6]
    energy = float((d1.x * np.minimum(d1.lam, theta)).sum())
    assert energy == pytest.approx(d1.analog_energy, rel=1e-6)
