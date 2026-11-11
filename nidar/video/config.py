"""Video-link configuration. Every field that depends on an open question has NO default.

``paper_pilot_profile`` returns the values Paper 1 used in its own pilot / examples, clearly labelled. It is
for simulation and tests only and is NOT a statement about our link (OQ-03, OQ-12, OQ-13, OQ-23, OQ-24).
Parameters follow [P1 §3.1, §D.2, Table 21]; "no default for open questions" is [TEAM-BRIEF §0.4].
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VideoLinkConfig:
    # --- source / GoP (OQ-12) ---
    luma_hw: tuple[int, int]              # H, W (multiples of 16)
    fps: float
    G: int                                # frames per GoP
    temporal: str                         # "haar" | "dct2" [P1 Def. 4]
    regions_luma: int                     # spatial regions per side, luma (chroma: half, min 1); pilot: 4 [P1 Table 21]
    credited_bits_per_sample: float       # T_min expressed in bit/sample of the reference format [P1 §D.2]
    # --- channel / resources (OQ-03, OQ-11, OQ-14) ---
    symbol_rate_hz: float                 # W_i, complex uses per second for this drone
    overhead_fraction: float              # delta in n = (1 - delta) W T_g (pilots counted separately)
    n_telemetry: int                      # channel uses per GoP reserved for telemetry (OQ-14)
    fading_blocks: int                    # L blocks per GoP (0 = AWGN)
    pilots_per_block: int                 # N_p [P1 Table 18]
    expected_snr_db: float                # open-loop channel quality for the gains [P1 Rem. 6]
    # --- floor (OQ-23) ---
    floor_rate_bits_per_use: float        # from a certified design (b_F / n_F) [P1 Prop. 18]
    floor_power_ratio: float              # P_F / P_bar (gamma_F relative to the mean; controller output)
    crc_bits: int                         # r [P1 Rem. 7]
    # --- refinement ---
    spreading: str                        # "identity" | "hadamard" (open, docs §4.9)
    limiter_backoff_db: float | None      # Lambda in dB above the mean analogue power; None = no limiter
    # --- decoder ---
    motion_search: str                    # "zero" (paper pilot) | "block" (decoder-side, Table 13 ph. 3)
    mismatch_threshold: float | None      # normalised-innovation test for the Rem. 5 fallback (OQ-32); None=off

    @property
    def t_g(self) -> float:
        return self.G / self.fps

    def samples_per_gop(self) -> int:
        h, w = self.luma_hw
        return self.G * h * w * 3 // 2

    def channel_uses(self) -> int:
        """n = (1 - delta) W T_g [P1 §3.1]."""
        return int((1.0 - self.overhead_fraction) * self.symbol_rate_hz * self.t_g)


def paper_pilot_profile(luma_hw: tuple[int, int] = (96, 128), snr_db: float = 10.0, fading_blocks: int = 0,
                        motion_search: str = "zero") -> VideoLinkConfig:
    """PAPER PILOT PROFILE - not our link.

    Mirrors [P1 §D.2, Table 21] scaled to a small frame: 25 fps, G = 8, 2 Mbps-equivalent at 720p25
    (0.0579 bit/sample), channel uses per sample as in the pilot (226,113 uses for 2,703,360 samples per GoP),
    AWGN by default. The floor rate is the AWGN capacity at the design SNR reduced by the Table 7 overhead.
    Regions are scaled so each region keeps the pilot's 160x88 luma size (metadata stays ~a pilot-like share).
    Choices with no paper value (power ratio 1, Hadamard spreading, no limiter, CRC-32, mismatch test off)
    are placeholders, named here so nothing is hidden.
    """
    import math

    from nidar.video.certificates.sizing import relative_overhead

    h, w = luma_hw
    regions = max(1, round(min(h / 88, w / 160)))   # keep the pilot's region size (640x352 / 4 = 160x88)
    k = 8 * h * w * 3 // 2
    uses_per_sample = 226_113 / 2_703_360
    n = int(uses_per_sample * k)
    g = 10 ** (snr_db / 10)
    credited = 0.0579 * k
    rate = math.log2(1 + g) / (1 + relative_overhead(max(credited, 1.0), g, 1e-3))
    return VideoLinkConfig(
        luma_hw=luma_hw, fps=25.0, G=8, temporal="dct2", regions_luma=regions, credited_bits_per_sample=0.0579,
        symbol_rate_hz=n / (8 / 25.0), overhead_fraction=0.0, n_telemetry=0, fading_blocks=fading_blocks,
        pilots_per_block=0 if fading_blocks == 0 else 6, expected_snr_db=snr_db,
        floor_rate_bits_per_use=rate, floor_power_ratio=1.0, crc_bits=32, spreading="hadamard",
        limiter_backoff_db=None, motion_search=motion_search, mismatch_threshold=None)
