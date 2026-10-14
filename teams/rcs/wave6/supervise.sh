#!/bin/bash
# Relaunch a guarded script whenever it exits early (e.g. memory guard), until it logs completion. Usage: supervise.sh controller|local
cd "$(dirname "$0")"
PY=/home/mike-anderson/dev/cohezion/.venv/bin/python
if [ "$1" = controller ]; then S=controller.py; L=results/controller.log; DONE="all cells terminal|STOP_COST present|deadline: remaining"
else S=local_runner.py; L=results/local.log; DONE="deadline reached|RSS cap exceeded|LOCAL_ALL_DONE"; fi
while true; do
  grep -qE "$DONE" "$L" 2>/dev/null && exit 0
  m=$(awk '/MemAvailable/{print $2}' /proc/meminfo)
  if [ "$m" -ge 20971520 ]; then
    echo "$(date +%T) supervisor: launching $S (MemAvailable ${m} kB)" >> "$L"
    BLUEQUBIT_ENV_FILE=/home/mike-anderson/dev/cohezion/.env OMP_NUM_THREADS=4 nice -n 10 $PY $S >> "$L" 2>&1; rc=$?
    if [ "$1" = local ] && [ $rc -eq 0 ]; then echo "LOCAL_ALL_DONE" >> "$L"; fi
  fi
  sleep 60
done
