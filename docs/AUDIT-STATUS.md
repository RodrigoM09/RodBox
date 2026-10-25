# Ongoing code audit

This is a partial, evidence-based review, not a completed every-line audit. The
broad independent AI review was interrupted; focused source and regression
validation continued separately. Device storage failures prevent safe installation
of prepared follow-ups. Native builds and mocks do not establish hardware health.

| Finding | Evidence and state |
| --- | --- |
| Reset error paths can leave the recursive ATA mutex held | PB17: three unlock-and-return corrections; 220 actual-function executions and native build pass; not installed |
| Copy writes were inside a Python assertion | Corrected separately; short writes preserve originals; ten copy tests pass in ordinary and optimized Python, sixteen companion tests overall |
| Library/index finalizers could publish after late write errors | PB18: successful flush and close required; actual-function error injection and native build pass; not installed |
| USB write-error recovery may re-arm an already pending OUT transfer | A host-only [reproducer](../tests/usb/reproduce_write_error.py) confirms overlapping receive requests after an injected disk error; correct BOT recovery still needs implementation and broader tests |
| ATA cache-flush errors may be hidden by lower layers | Error propagation and target capability need further review; no speculative flush-policy patch installed |
| Sound-analysis working-header writes/periodic flushes ignore some failures | Follow-up required; PB18 protects final publication only |
| New station engine lifecycle is unfinished | Not integrated/built/shipped; queue ownership, append-without-restart, continuation and USB/shutdown tests still required |

The deployed PB16 passed startup, small normal-file USB tests and fresh readbacks
of saved additions, then failed the following write. A later small firmware stage
also failed readback; the active firmware remained unchanged. Screen sleep is not
an established explanation. Stop retrying writes on the affected player and
preserve verified backups while checking cable, transport, adapter and cards.

Review priorities continue with storage-error recovery, file durability, analysis
lifecycle, database/audiobook progress, playback/control/DSP, skin/display geometry
and station integration. No claim is made that all themes, codecs, accessories or
possible concurrent schedules have been validated. See [testing](TESTING.md),
[credits](../CREDITS.md) and the separate PB17/PB18 notes for exact limits.

The data filesystem was subsequently repaired without formatting. Verified files
were restored from independent backups, and final file/checksum/filesystem checks
passed. Playback checks after a clean shutdown/restart also passed, but the next
read-only disk check found fresh corruption before any PB17 staging. Updates and
bulk transfer are paused. This is recovery evidence, not proof that the root
cause or sustained USB reliability is fixed. See [filesystem recovery](FILESYSTEM-RECOVERY.md).
