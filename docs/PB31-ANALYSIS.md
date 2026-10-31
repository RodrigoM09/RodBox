# PB31 analysis error handling — 2026-10-31

PB30 could silently skip every track when the analysis worker could not start, then report completion. PB31 stops on that failure, preserves unfinished work when saving succeeds, and reports worker and save failures separately. No failed worker attempt counts as a measured or skipped track, and the scan does not publish a completed index on this path.

Startup memory, index-open and busy-database errors now stay visible until dismissed. Index allocation failures receive a specific memory message instead of the generic index-open message.

Both Quick and Thorough analysis still require external power. Without it, the scan waits for a charger; unplugging pauses it. A wall USB charger is suitable. These requirements were not introduced by PB31. The user's original message was not captured, so neither missing power nor worker exhaustion is established as the cause of that incident.

## Verification

- Three focused ASan/UBSan suites passed: `test_scan_save_failure.py`, `test_index.py`, and `test_power.py` in `tests/analysis/`.
- The worker-failure regression verifies no record insertion, no false progress, and a stop result. Index tests cover persistence failures and resume; power tests cover connection, removal and controls.
- Native ipod6g / S5L8702 / 64 MB core and codecs build passed with Arm GNU Toolchain 13.2.Rel1. No codec source changes.
- Installation replaced only the core and version file. All 42 firmware hashes passed, 1,366 protected files were backed up, and unchanged protected files were verified afterward.
- Filesystem checks before and after passed. The 2,243-file music inventory retained its sizes and modification times; no music writes, formatting or repairs. Full music checksums were not repeated.
- Device safely ejected. PB31 reboot and on-device analysis acceptance are pending. This does not establish a fix for the unconfirmed original symptom.

PB30's FAT directory fix, PB29 navigation behavior and previous changes remain. This checkpoint publishes source, tests and sanitized results; personal device scripts, backups, media and binary build artifacts are not included.
