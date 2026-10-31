# PB32 battery percentage continuity — 2026-10-31

The Classic charging table maps 3998 mV to 42%, while its discharge table maps the same voltage to 82%. Switching power state therefore explained a reproducible percentage discontinuity without any actual increase in stored charge.

PB32 applies a Classic-only monotonic display estimate: percentage cannot rise while discharging or fall while charging, except that an empty reading takes priority. Invalid readings remain invalid. At startup, the selected voltage curve supplies the initial estimate. Existing millivolt shutdown thresholds and charging control remain unchanged. All earlier firmware fixes are retained.

This is continuity handling, not a calibrated fuel gauge. The estimate can plateau until the new curve catches up, and voltage-based startup estimates can differ. The earlier unexpected shutdown/DFU incident remains unexplained; this change does not establish its cause or prove battery health.

## Verification

Three focused ASan/UBSan suites passed: `tests/analysis/test_battery_transition.py`, `test_power.py`, and `test_usb_battery.py` (the latter two in the same directory). The transition test reproduces 42/82 from the actual voltage tables and checks plug/unplug continuity, charge/discharge progression, full, empty and invalid readings. Native ipod6g / S5L8702 / 64 MB core and codecs build passed with Arm GNU Toolchain 13.2.Rel1.

Installation backed up 1,366 protected files and replaced only the core and version file. All 42 firmware files verified; filesystem checks passed before and after. Music inventory sizes and modification times were unchanged for 2,243 files. No formatting, repairs or music writes; full music checksums were not repeated.

The user confirmed normal PB32 startup and unchanged percentage when plugging/unplugging the charger. Subsequent read-only verification passed: 42 firmware hashes, database structure with 1,592 active tracks and no duplicate unique-tag values, 86 artist-image hashes, and 765 cached-image structures. The filesystem check exited 0 with no cross-links or orphan clusters. The existing partition-space advisory was not repaired or treated as filesystem corruption.

PB31 Thorough-analysis hardware acceptance is still pending. No private identifiers, media, configs, raw device logs, installer scripts or binaries are included in this source checkpoint.
