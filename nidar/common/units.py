"""SI units, mission constants and frame helpers.

Frames: local inertial F_I (metres), body F_B; quaternions are unit, scalar-first, body->inertial
[P2 §1.2 Eq. 8-9]. Every constant below cites its source; nothing here is a design choice.
"""
from __future__ import annotations

import numpy as np

# --- Constants from the sources -------------------------------------------------------------
FT_TO_M = 0.3048                         # exact definition of the international foot
G_MPS2 = 9.81                            # gravity magnitude used by Paper 2 [P2 Eq. 10, 155]
PAYLOAD_KG = 0.200                       # kit mass [BRIEF §2] [P2 Eq. 13]
PAYLOAD_BOX_M = (0.20, 0.10, 0.05)       # l x b x h [BRIEF §2]
FLEET_MAX_KG = 25.0                      # combined all-up weight cap [BRIEF §2]
MISSION_AREA_MAX_M2 = 100_000.0          # 10 hectares [BRIEF §1] [P2 §1.1]
MAX_SURVIVORS = 10                       # [BRIEF Scenario, §1]
MAX_FLIGHT_S = 30 * 60.0                 # [BRIEF §3]
SETUP_MAX_S = 300.0                      # [BRIEF §3] [P2 §12.4]
LAUNCH_PAD_SIDE_M = 12 * FT_TO_M         # 12 ft x 12 ft = 3.6576 m [BRIEF §7] [P2 §15.3.1]
MIN_DRONES = 2                           # [BRIEF §1]


# --- Quaternion helpers [P2 §1.2, §4.1 Eq. 70-74] --------------------------------------------
def quat_normalize(q: np.ndarray) -> np.ndarray:
    """Return q / ||q||; raises ValueError for a zero quaternion."""
    q = np.asarray(q, dtype=float)
    n = float(np.linalg.norm(q))
    if q.shape != (4,) or n == 0.0:
        raise ValueError(f"quaternion must be a non-zero (4,) vector, got shape {q.shape}, norm {n}")
    return q / n


def quat_to_rotmatrix(q: np.ndarray) -> np.ndarray:
    """Rotation matrix R(q) in SO(3), body->inertial, for a scalar-first unit quaternion."""
    w, x, y, z = quat_normalize(q)
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
            [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
            [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
        ]
    )


def db_to_linear(db: float) -> float:
    """Power ratio from decibels (SNR conventions of [P1])."""
    return 10.0 ** (db / 10.0)


def linear_to_db(x: float) -> float:
    """Decibels from a power ratio; raises ValueError for x <= 0."""
    if x <= 0:
        raise ValueError(f"power ratio must be > 0, got {x}")
    return 10.0 * float(np.log10(x))
