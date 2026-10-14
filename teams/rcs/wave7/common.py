"""rcs wave 7 shared constants (pure data)."""
import sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "teams/rcs/wave6"))   # mirror_lib (circuit derivation, unchanged, read-only)
_r = np.random.default_rng(20260926)                 # identical to wave 6 plan.INPUTS
INPUTS = [[[int(b) for b in _r.integers(0, 2, 61)] for _k in range(2)] for _i in range(3)]
INPUT16 = [int(b) for b in np.random.default_rng(16).integers(0, 2, 16)]
Y16 = [[int(b) for b in np.random.default_rng(7).integers(0, 2, 16)] for _ in range(8)] + [INPUT16]
DEADLINE_ISO = "2026-10-01T20:00:00-04:00"
THREADS_DEFAULT = 8
PILOT_CHI, PILOT_DEPTHS = 64, (16, 20)
LADDER = (128, 256, 512)
N_SELECT = 6
C_TOL_REL = 1e-3          # C1/C2 reproduction tolerance (relative)
C3_TOL_ABS = 1e-7         # 16q forward amplitude tolerance
M_MIN_ERR = 1e-3          # a mutation must produce at least this amplitude error
