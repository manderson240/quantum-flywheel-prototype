# Freeze-coverage attestation (wave2), written 2026-10-06T14:18:15-04:00

DEFECT D187: `PREREG.sha16` = `04570ab6a4efeb79` covers only the first 319 bytes, the file header. The freeze rule "bytes up to and
including the line `## Addendum …`" was implemented with `find()`, which matched the marker text inside the sentence that
explains the rule, not the real addendum line. The protocol body (25130 bytes up to the real marker) was NOT cryptographically frozen.

Independent evidence that the body did not change after the freeze (2026-09-27T13:14:24-04:00): the Claude Code transcripts record every write to
this file. After the freeze the only writes were 17:14:57Z append (addendum); 17:18:57Z/17:19:05Z replaced the addendum's own '- Deviations: none.' line (text now at byte 26658, addendum starts 25015). Reconstructed 2026-10-06 (reviews/fullaudit and session transcript
9c481e1e…, subagent transcripts under ~/.claude/projects).

Post-hoc body hash (sha256 of bytes up to and including the REAL addendum line), recorded now: `7b314a3aeee346e0bd5986d261a2701806d0d5810c912dc6e50cc670b9f3c299`.
This is an attestation of the current body, NOT a pre-registration freeze. The application does not claim a hash freeze
for this benchmark: it says "sealed key" (wave 2) and "pre-registered" (wave 3, written before its corpus existed).
