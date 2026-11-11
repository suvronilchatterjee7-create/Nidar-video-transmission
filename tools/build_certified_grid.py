"""Offline generation of the certified floor-design grid (versioned JSON loaded at setup).

For each floor mean SNR gamma_F in the list, find the smallest n_F (multiple of L) whose KL upper bound on
eps_DT(B_F + 1) is <= eps_core / 2 [P1 Thm 1, Prop. 11]; the controller may only use these designs
[P1 Prop. 18]. Runtime only loads the file, so runtime safety never depends on runtime sampling.
[ADIAT-inspired: versioned result files]

Example (paper's Table 9 point):
  python tools/build_certified_grid.py --out grid.json --b-f 533333 --L 16 --eps-core 1e-3 \
      --gamma-db 9 10 11 --n-total 1333333 --margin-db 0
Clipping and channel-estimation error are NOT in this certificate (docs/VIDEO_SUBSYSTEM.md P-7).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # run from a checkout without installing

from nidar.common.contracts import CertifiedFloorDesign  # noqa: E402
from nidar.video.certificates.dt_bound import certify_floor  # noqa: E402
from nidar.video.certificates.grid import CertifiedGrid  # noqa: E402


def build(b_f: int, L: int, eps_core: float, gammas_db: list[float], n_total: int, margin_db: float,
          draws: int, seed: int, delta: float) -> CertifiedGrid:
    designs = []
    for g in gammas_db:
        n_f, est = certify_floor(b_f, L, g, eps_core, L, n_total, draws, seed, delta)
        designs.append(CertifiedFloorDesign(
            design_id=f"L{L}_g{g:g}dB_B{b_f}", gamma_f_db=g, n_f=n_f, L=L, m=n_f // L, b_f_bits=b_f,
            eps_core=eps_core, margin_db=margin_db, dt_upper_bound=est.p_bar, n_samples=est.n_samples,
            confidence_delta=delta))
    return CertifiedGrid(designs)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--b-f", type=int, required=True)
    ap.add_argument("--L", type=int, required=True)
    ap.add_argument("--eps-core", type=float, required=True)
    ap.add_argument("--gamma-db", type=float, nargs="+", required=True)
    ap.add_argument("--n-total", type=int, required=True)
    ap.add_argument("--margin-db", type=float, required=True)
    ap.add_argument("--draws", type=int, default=1_000_000)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--delta", type=float, default=1e-6)
    a = ap.parse_args(argv)
    grid = build(a.b_f, a.L, a.eps_core, a.gamma_db, a.n_total, a.margin_db, a.draws, a.seed, a.delta)
    grid.save(a.out)
    for d in grid.designs:
        print(f"{d.design_id}: n_F={d.n_f} ({d.n_f / a.n_total:.3%} of the GoP), p_bar={d.dt_upper_bound:.3e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
