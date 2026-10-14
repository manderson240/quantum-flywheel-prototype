# Deviations from PREREG (sha16 9f4b9c16548a8339)

## DV1 — parser: measurement register name (16:02, before any mirror count was seen)
- Run 1 (16:02:16) made all 3 mirror circuits MISSING: `unsupported gate 'meas'`. The mirror files use Qiskit's
  `measure_all()` register (`bit[61] meas;`, `meas[i] = measure q[i];`). PREREG §2 listed only `c[..] = measure q[..]`.
- The failure is in MY parser's register-name pattern, not in the data. Applied literally, PREREG §5 would report
  the whole test MISSING because of it. Change: the measurement pattern accepts any classical register name
  (`<ident>[i] = measure q[j]`). No other parser rule changed. Run 1 output (only the error list and the K3/K4
  counts, which were not inspected before this change) is kept in results/run1_missing/.
- Label: POST-HOC PARSER FIX made after seeing an error message but before seeing any mirror gate count.
  The counting rules, model and decision rule are unchanged.

## DV2 — memory floor breached on the 16:02:50 run
- The run started at MemAvailable 20,432,356 kB = 19.49 GiB, below the 20 GiB floor (PREREG §5 required a wait).
- It was rerun unchanged at 16:03:51, after a compliant check (22,089,364 kB = 21.07 GiB). bias_test.json is
  identical apart from rss_mb. The reported results are from the compliant run. Peak RSS was 17 MB.
