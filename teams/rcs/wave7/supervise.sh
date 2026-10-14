#!/bin/bash
# rcs wave 7: relaunch the guarded runner whenever it exits early (memory guard / mem wait), until RUN_COMPLETE.
cd "$(dirname "$0")"
PY=/home/mike-anderson/dev/cohezion/.venv/bin/python
L=results/runner.log
while true; do
  [ -f results/RUN_COMPLETE ] && exit 0
  m=$(awk '/MemAvailable/{print $2}' /proc/meminfo)
  if [ "$m" -ge 20971520 ]; then
    echo "$(date '+%m-%d %T') supervisor: launching runner (MemAvailable ${m} kB)" >> "$L"
    nice -n 10 $PY runner.py >> "$L" 2>&1
  else
    echo "$(date '+%m-%d %T') supervisor: WAIT MemAvailable ${m} kB < 20 GiB" >> "$L"
  fi
  [ -f results/RUN_COMPLETE ] && exit 0
  sleep 120
done
