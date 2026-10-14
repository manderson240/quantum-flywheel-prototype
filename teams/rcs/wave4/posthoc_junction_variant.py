"""POST-HOC (not pre-registered): apply the PREREG §4 rule to the junction-cancelled variant. No verdict weight."""
import json
from pathlib import Path

R = Path(__file__).resolve().parent / "results"
b = json.loads((R / "bias_test.json").read_text())
i, cat = b["inputs"], b["categories"]
nm = b["variant_junction_cancelled"]["N_m"]
dn = {"cz": cat["cz"]["K3_mean"] - nm, "rx": 0.0, "cz_layers": 0.0}  # cancelling one CZ run merges no 1q layer
g_c = i["c"] * dn["cz"]
g_cmax = i["c_max"] * dn["cz"]
g_all = i["D"] * max(0.0, dn["cz"] / cat["cz"]["K3_mean"])


def rule(t):
    if g_c >= t:
        return "EXPLAINS"
    if g_all < t:
        return "CANNOT EXPLAIN"
    return "PARTLY EXPLAINS"


out = {"label": "POST-HOC variant reading; junction duplicate is present in the logical circuit with barriers; "
                 "native execution untested",
       "N_m": nm, "dN_cz": dn["cz"], "G_c": g_c, "G_cmax": g_cmax, "G_all": g_all, "G_c_over_g": g_c / i["g_ln_gap"],
       "rule_thr": rule(i["thr"]), "rule_thr_alt": rule(i["thr_alt_sigma0.0506"])}
(R / "posthoc_junction_variant.json").write_text(json.dumps(out, indent=1))
print(out)
