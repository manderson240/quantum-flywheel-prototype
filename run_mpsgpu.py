"""PREREG_MPSGPU.md runner: V-GPU validation at chi=512, then chi=2048 on 74qx27c and 51qx30c only if the measured-cost
prediction fits the credit cap and the 7 h ceiling. Job ids go to the journal at once; results to results/mpsgpu.json.
Token read in-process, never printed. Resumable: finished steps are skipped."""

import json
import time

import bluequbit
from cost_ledger import CAP, ok_to_spend, record_cost, record_job, spent
from floquet_any import load, magnetization
from kicked_ising_crosscheck import OUT, load_token


CPU_512 = 0.5583479436611802
TERM = {
    "COMPLETED",
    "FAILED_VALIDATION",
    "NOT_ENOUGH_FUNDS",
    "CANCELED",
    "TERMINATED",
    "JOBS_LIMIT_EXCEEDED",
}
FILES = {
    "51qx30c": "floquet_mixed_field_ising_mag_51qx30c.qasm",
    "74qx27c": "floquet_mixed_field_ising_mag_74qx27c.qasm",
}
PATH = OUT / "mpsgpu.json"
bq = bluequbit.init(load_token())
state = json.loads(PATH.read_text()) if PATH.exists() else {}


def save():
    PATH.write_text(json.dumps(state, indent=1))


def run_step(key, tag, chi, rate_per_h=None):
    """Submit, record, poll every 3 min; cancel if billing would pass CAP or at 7.5 h. Returns the step record."""
    if state.get(key, {}).get("status") in TERM | {"NOT RUN"}:
        return state[key]
    rec = state.setdefault(key, {})
    if rec.get("job_id"):  # resume polling; never resubmit a paid job
        print(key, "resuming", flush=True)
    else:
        qc, n, _ = load(FILES[tag])
        job = bq.run(qc, device="mps.gpu", pauli_sum=magnetization(n), options={"mps_bond_dimension": chi},
                     force_run=True, asynchronous=True)
        rec.update(tag=tag, chi=chi, job_id=job.job_id, submitted=time.time())
        save()
        record_job(job.job_id, device="mps.gpu", purpose=f"PREREG_MPSGPU {key}", tag=tag)
        print(key, "submitted", job.job_id, flush=True)
    jid = rec["job_id"]
    budget_left = CAP - spent()
    while True:
        time.sleep(180)
        try:
            r = bq.get(jid)
        except Exception as e:
            print(key, "get error", str(e)[:120], flush=True)
            continue
        el_h = (time.time() - rec["submitted"]) / 3600
        if r.run_status in TERM:
            break
        if not rec.get("cancelled_backstop") and (el_h > 7.5 or (rate_per_h and el_h * rate_per_h > budget_left)):
            print(key, "CANCEL backstop at", round(el_h, 2), "h", flush=True)
            bq.cancel(jid)
            rec["cancelled_backstop"] = True
    rec.update(
        status=r.run_status,
        wall_h=round(el_h, 3),
        cost=r.cost,
        value=float(r.expectation_value) if r.run_status == "COMPLETED" else None,
        err=(r.error_message or "")[:240],
    )
    record_cost(jid, r.cost, device="mps.gpu", tag=tag)
    save()
    print(
        key,
        rec["status"],
        rec["value"],
        "cost",
        rec["cost"],
        "h",
        rec["wall_h"],
        "| spent",
        round(spent(), 2),
        flush=True,
    )
    return rec


if __name__ == "__main__":
    # Step 1: V-GPU
    assert ok_to_spend(1.0), "cap"
    v = run_step("V_51qx30c_chi512", "51qx30c", 512, rate_per_h=4.0)  # list rate: backstop only (prereg)
    ok = (
        v["status"] == "COMPLETED"
        and v["value"] is not None
        and abs(v["value"] - CPU_512) <= 1e-3
        and v["cost"] is not None
    )
    state["V_GPU_pass"] = ok
    save()
    if not ok:
        print("STOP: mps.gpu not validated", flush=True)
        raise SystemExit(0)
    C1, T1 = float(v["cost"]), float(v["wall_h"])
    rate = C1 / T1 if T1 > 0 else None
    for key, tag, scale in (
        ("74qx27c_chi2048", "74qx27c", 64 * 74 / 51),
        ("51qx30c_chi2048", "51qx30c", 64),
    ):
        if state.get(key, {}).get("status"):
            continue
        C, T = C1 * scale, T1 * scale
        if spent() + C > CAP or T > 7.0:
            state[key] = {
                "status": "NOT RUN",
                "reason": f"predicted ${C:.2f} / {T:.2f} h vs remaining ${CAP - spent():.2f} / 7 h",
            }
            save()
            print(key, "NOT RUN", state[key]["reason"], flush=True)
            continue
        state[key] = {"predicted_cost": C, "predicted_h": T}
        save()
        rec = run_step(key, tag, 2048, rate_per_h=rate)
        rec.update(predicted_cost=C, predicted_h=T)
        save()
    print(
        "RUN_MPSGPU_DONE",
        json.dumps({k: state[k].get("status") for k in state if isinstance(state[k], dict)}),
        flush=True,
    )
