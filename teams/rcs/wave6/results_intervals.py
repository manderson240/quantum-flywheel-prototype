import sys; m=int(next(l for l in open('/proc/meminfo') if l.startswith('MemAvailable')).split()[1]); sys.exit(f'MemAvailable {m/2**20:.1f} GiB < 20') if m < 20*2**20 else None
"""POST-HOC uncertainty statements for the write-up (A8): exact Poisson (Garwood) 95% interval on the pooled BlueQubit
d36 chi=256 hits, and per-instance ratio range for own-MPS. Writes results/intervals.json."""
import json
from pathlib import Path
from scipy.stats import chi2
HERE = Path(__file__).resolve().parent
a = json.loads((HERE / "results" / "analysis.json").read_text())
F_hw = a["hardware"]["36"]["F"]
k, n = 4, 400_000
lo, hi = chi2.ppf(0.025, 2 * k) / 2, chi2.ppf(0.975, 2 * (k + 1)) / 2
own = a["own_table"]["256"]["36"]["p_i"]
bq = a["bq_table"]["256"]["36"]
out = {"bq_chi256_d36": {"hits": k, "shots": n, "garwood95_counts": [lo, hi], "survival95": [lo / n, hi / n],
                          "ratio95": [F_hw / (hi / n), F_hw / (lo / n)], "ratio_ivw_point": F_hw / bq["F"], "pooled_plain": k / n,
                          "ratio_plain_point": F_hw / (k / n)},
       "own_chi256_d36": {"per_instance": own, "per_instance_ratio": [F_hw / p for p in own]}}
(HERE / "results" / "intervals.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
