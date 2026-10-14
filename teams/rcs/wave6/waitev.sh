#!/bin/bash
# wait (<=580 s) for a new DONE/BAD/CANCEL/NOTRUN line in controller.log beyond count $1
cd "$(dirname "$0")/results"
timeout 580 bash -c "until [ \$(grep -cE 'DONE|BAD|CANCEL|NOTRUN|terminal' controller.log) -gt $1 ]; do sleep 20; done"
echo "count=$(grep -cE 'DONE|BAD|CANCEL|NOTRUN|terminal' controller.log)"; grep -v "WARN\|INFO" controller.log | tail -4; date +%T; tail -1 local.log
