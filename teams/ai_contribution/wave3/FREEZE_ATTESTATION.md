# Freeze-coverage attestation (wave3), written 2026-10-06T14:35:08-04:00 (regenerated after an interrupted mutation test removed the first copy)

DEFECT D187: `PREREG.sha16` = `b20ba288605a1338` covers only the first 345 bytes, the file header. The freeze rule "bytes up to and
including the line `## Addendum …`" was implemented with `find()`, which matched the marker text inside the sentence that
explains the rule, not the real addendum line. The protocol body (21559 bytes up to the real marker) was NOT cryptographically frozen.

Independent evidence that the body did not change after the freeze (2026-09-27T23:47:01-04:00): the Claude Code transcripts record every
write to this file. After the freeze the only write was the 03:48:10Z append of the addendum. Reconstructed 2026-10-06.

Post-hoc body hash (sha256 of bytes up to and including the REAL addendum line), recorded now: `362958bf01e16a015d42edb4260bbf0300a566bbf902aae308e901802034ae34`.
This is an attestation of the current body, NOT a pre-registration freeze. The application calls this benchmark's brief
"pre-registered" (written before its corpus existed); it does not claim a hash freeze.
