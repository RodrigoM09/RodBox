# Verification and its limits

The checkpoint-specific installation and pending notes below describe evidence at their original stages. For current cumulative acceptance, see [PB27 database uniqueness](PB27-DATABASE-UNIQUENESS.md).

## Focused tests

From the repository root:

```sh
python3 -m unittest discover -s companion -p 'test_*.py'
python3 tests/usb/test_write_length.py firmware-source/firmware/usbstack/usb_storage.c
python3 tests/usb/test_endpoints.py firmware-source/firmware/drivers/usb-designware.c
python3 tests/playlist/test_guard.py firmware-source/apps-ipod/playlist/playlist.c
python3 tests/playlist/test_compare_benchmark.py firmware-source/apps-ipod/playlist/playlist.c
python3 tests/analysis/test_probe.py
python3 tests/analysis/test_index.py
python3 tests/analysis/test_power.py
python3 tests/analysis/test_plug_wake.py
python3 tests/analysis/test_usb_battery.py
python3 tests/storage/test_usb_idle.py
python3 tests/storage/test_sector_cache.py
```

Host C harnesses require clang and use AddressSanitizer/UndefinedBehaviorSanitizer. External hardware services are mocked. They exercise the extracted active function bodies; they are not a USB bus, decoder or storage-device emulator. Never send deliberately malformed write traffic to a filesystem containing your music.

PB19's [sector-cache regression](SECTOR-CACHE.md) uses a byte-exact mock disk
with the real shared ATA cache/read/write region. It covers stale reads,
neighboring-sector rollback, ambiguous failed writes, 40,000 mixed operations
across single/multidrive configurations and native 4K access. It passes with
ASan/UBSan; the original code and each missing-invalidation mutation fail.
The native ipod6g build and preceding 220 ATA policy/reset executions pass.
PB19 remains uninstalled; these are host checks, not hardware acceptance.

Recorded checks: 17 USB write-length/state/residue cases; 11 endpoint/IRQ/blocking-return cases; 21 playlist guard/queue/replay/capacity cases; 50,000 old/new insertion comparisons. Companion fixtures cover interrupted/failed copies, containment, source changes, existing-file preservation and rejection of incomplete scans.

The playlist comparison benchmark runs on the host, not on the iPod. One recorded 16,000+1,000-entry run gave approximately 1.36x prepend and 1.61x middle; append was essentially unchanged at this scale. Do not translate that into a battery or device-speed guarantee.

## Device acceptance sequence

Back up firmware/settings/progress first. Add one isolated change; build and run its focused tests. Install only matching required files, compare expected hashes, unmount/remount and compare again. Test normal disposable transfers around the build's USB buffer size (24 KiB on the recorded ATA build) and a multi-megabyte file. Flush writes, bypass host read cache where supported, and compare hashes after remount. Remove only the test files created for the check. Run read-only filesystem verification.

Safely eject, fully restart, then check music playback, queue order, shuffle from an audiobook, headset controls and audiobook resume. Reconnect and repeat normal USB/remount/filesystem checks under the newly running firmware. Installation-time transfer checks run under the old firmware until restart; do not label them post-reboot acceptance.

PB7–PB10 completed that sequence. PB10's post-restart checks included 24 KiB boundary transfers and a 4 MiB transfer verified after remount, followed by read-only filesystem verification. PB11's analysis corrections pass 58 synthetic probe checks, legacy index upgrade/resume/cache tests and the native build. Its on-device analysis and playback acceptance are pending. See [NATIVE-ANALYSIS.md](NATIVE-ANALYSIS.md). No calibrated analog-output test, noise-floor measurement, long battery comparison or comprehensive digital-dock validation was completed.

PB11's first scan was blocked by the qualified-charger gate. PB12 corrects that
gate and adds battery/power visibility and the Scrim analysis icon. Seven actual
scan-control cases and the native build pass; both Scrim files pass the current
skin parser. Installed firmware/theme hashes pass after remount and the
filesystem is verified. Device analysis, visual and post-restart USB checks
remain pending; see [POWER-AND-BATTERY.md](POWER-AND-BATTERY.md).

PB13 adds three battery-display modes with the existing integer layout and
preserved graphic/numeric config tokens. Its native build and both Scrim parser
checks pass; font metrics fit the percentage and clock in separate viewports.
Installed mode/layout, persistence and post-restart USB checks remain pending;
see [BATTERY-DISPLAY.md](BATTERY-DISPLAY.md).

PB14 is installed with verified before/after backups after analysis completed.
Only the core, matching information, Now Playing skin and menu order changed;
the completed sound index and audiobook progress were preserved. Fifteen actual-helper
input-transition cases pass ASan/UBSan and the native build passes. Physical
charger/computer wake, normal timeout, reconnection and USB checks are pending;
see [PLUG-IN-WAKE.md](PLUG-IN-WAKE.md).

PB15's native build and 24 actual-renderer framebuffer cases pass. The USB
header fix removes stale theme pixels while retaining the detailed footer and
three battery modes. Physical visual and post-restart USB checks remain
pending; see [USB-HEADER.md](USB-HEADER.md).

PB16's native build and 33 actual-function scenarios in four host configurations
pass. The storage harness mocks hardware/scheduling and explicitly excludes
the existing error macros' signed-shift convention from UBSan. Runtime USB
storage, playback and resume acceptance remain pending. The identified sleep
weakness is not a proven explanation of the original corruption; see
[USB-STORAGE-AWAKE.md](USB-STORAGE-AWAKE.md).

## Cumulative durability tests

From the repository root run `python3 run_audit_tests.py`. Clang/cc and Python 3 are required. The playlist guard is generated before its comparison benchmark; generated files and verification logs are ignored. Tests use synthetic inputs and mocked hardware, never an attached player. PB28 passed all 47 suites on 2026-10-30, retaining PB27's database-alignment regression and adding the unmount-reader cleanup regression. The focused publication rerun also passed. The complete PB27 library restore and full post-repair checksum pass finished successfully; subsequent cache-related orphan clusters prompted PB28. Its first restart/reconnect passed, but repeated cache/USB and long-term acceptance remain open. See [PB28 details](PB28-ARTWORK-CLEANUP.md).

## Replaced-file readers during USB handover

Run `python3 tests/storage/test_unmount_removed_reader.py`. With `--source-root /path/to/older/firmware-source`, the same harness reproduces the PB27 failure. It uses production callback/close code with mocked storage/bookkeeping, not a physical FAT image or complete scheduler.

For device acceptance, begin with a verified clean filesystem and a backup. Exercise artwork generation/replacement and browsing, allow normal shutdown or USB handover, then verify artwork and the filesystem after reconnect. Distinguish original-image hash checks, cached-image structural checks and a full music checksum comparison; they establish different things. PB28 has one clean recorded restart/reconnect, not a completed stress campaign.

## PB29 navigation acceptance

PB29's native build and installation/remount firmware, artwork and filesystem checks passed. Its return paths were reviewed against the active source; the complete 47-suite run is PB28 evidence and was not repeated for this navigation-only change. On-device PB29 startup and both Menu paths remain pending. Follow the two routes in [PB29-NAVIGATION.md](PB29-NAVIGATION.md), including backing completely out to the main menu before selecting Now Playing again. This distinguishes the immediate entry route from the song's earlier browse history.
