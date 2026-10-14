"""Frozen cell list and inputs for rcs wave 6 (referenced by PREREG.md). Pure data, no I/O."""
import numpy as np

_r = np.random.default_rng(20260926)
INPUTS = [[[int(b) for b in _r.integers(0, 2, 61)] for _k in range(2)] for _i in range(3)]  # INPUTS[inst][k]
INPUT16 = [int(b) for b in np.random.default_rng(16).integers(0, 2, 16)]
INPUT_V3 = [1] + [0] * 60  # only qubit 0 flipped (endianness control)
DEPTH_ORDER = [28, 20, 32, 24, 16, 12, 8]


def shots_for(chi):
    return 200_000  # DEVIATIONS D5 (was 1e6 for chi <= 256)


def cell(cid, n, inst, d, chi, inp, shots=None, group="main", bits=None):
    b = bits if bits is not None else INPUTS[inst][inp]
    return {"id": cid, "n": n, "inst": inst, "d": d, "chi": chi, "input_idx": inp, "bits": b,
            "shots": shots if shots is not None else (shots_for(chi) if isinstance(chi, int) else None), "group": group}


def bq_cells():
    """BlueQubit cells in frozen priority order. 'CHI_TOP' depth-scan cells are resolved at run time (PREREG §5)."""
    c = [cell("V3_61q_d2_chi64", 61, 0, 2, 64, None, 10_000, "validation", INPUT_V3),
         cell("V1_16q_d36_chi256", 16, 0, 36, 256, None, 100_000, "validation", INPUT16)]
    c += [cell(f"V2_16q_d36_chi{x}", 16, 0, 36, x, None, 100_000, "validation", INPUT16) for x in (4, 8, 16)]
    c += [cell("P1_i0_d36_chi128", 61, 0, 36, 128, 0, group="pilot"),
          cell("P2_i0_d36_chi256", 61, 0, 36, 256, 0, group="pilot")]
    c += [cell(f"M_i{i}_d36_chi256", 61, i, 36, 256, 0) for i in (1, 2)]
    c += [cell(f"M_i{i}_d36_chi128", 61, i, 36, 128, 0) for i in (1, 2)]
    for x in (512, 1024, 2048):
        c += [cell(f"M_i{i}_d36_chi{x}", 61, i, 36, x, 0) for i in (0, 1, 2)]
    c += [cell(f"S_top_i{i}_d{d}", 61, i, d, "CHI_TOP", 0, group="scan_top") for d in DEPTH_ORDER for i in (0, 1, 2)]
    c += [cell(f"S256_i{i}_d{d}", 61, i, d, 256, 0, group="scan_256") for d in DEPTH_ORDER for i in (0, 1, 2)]
    c += [cell(f"I2_i{i}_d36_chi256", 61, i, 36, 256, 1, group="input2") for i in (0, 1, 2)]
    c += [cell("F_full_d36_logical", 61, None, 36, "CHI_TOP", None, 200_000, "feasibility", [0] * 61)]
    return c


def local_cells():
    """Own-numpy-MPS cells (exact survival of the truncated state, no sampling), frozen order."""
    c = []
    for x in (16, 32, 64, 128):
        c += [cell(f"L_chi{x}_i{i}_d{d}", 61, i, d, x, 0, 0, "local") for d in (36, 32, 28, 24, 20, 16, 12, 8) for i in (0, 1, 2)]
    c += [cell(f"L_chi256_i{i}_d{d}", 61, i, d, 256, 0, 0, "local") for d in (36, 28, 20, 32, 24, 16, 12, 8) for i in (0, 1, 2)]
    return c
