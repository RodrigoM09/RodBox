# PB24–PB26: current experimental status

Updated 2026-10-29. PB26 (`rodbox-pb26-dbbootstrap-261028`) is the latest experimental source checkpoint for ipod6g / S5L8702 / 64 MB. It preserves the earlier PodBox/Scrim, Music/Audiobooks, native progress, artwork, analysis and input adaptations plus the [PB20–PB23 durability changes](PB20-PB23-DURABILITY.md). The unfinished station engine remains excluded. The bootloader was not changed.

## Focused changes

- **PB24:** Decode the ATA model to recognize iFlash alongside standard SSD hints; preserve explicit HDD/SSD mode choices and wake using the old mode before changing it. For non-PM ATA adapters, settle after flush and retain the power rail while clock-gated; do not enter the old timed deep-power-cut path. Actual-source tests cover synthetic IDENTIFY words, mode overrides, failed wakes and idle power sequencing. These policies are experimental, not proof that a power transition caused the observed corruption.
- **PB25:** Reject a second transfer on an already-busy non-control DesignWare endpoint before overwriting the original request address/size. Preserve EP0 control replacement behavior. The extracted-production regression reproduces the earlier overwrite and checks both endpoint directions and EP0 behavior. No captured trace establishes this as the physical corruption trigger.
- **PB26:** Initial tagcache commits could see too little free memory even when playback held reclaimable memory. Request a bounded buffer based on `commit_need`, invoking the existing shrink mechanism, then return the playback reserve before retaining the immovable merge buffer. Remove redundant startup preallocation. The production allocator regression reproduces PB25’s failure and covers headroom, ordinary allocation, allocation/shrink failures and no-memory refusal.

AI assistance was used for focused review, implementation, regression tests, builds and this record. Upstream attribution and licenses are retained in [CREDITS.md](../CREDITS.md).

## Build and test evidence

All candidates built with Arm GNU Toolchain 13.2.Rel1 and 40 matching codecs. PB24 and PB25 each passed 44 host suites at preparation; PB26 passed 45, including a fresh publication run on 2026-10-29. `python3 run_audit_tests.py` runs the cumulative synthetic/mocked tests; it never writes to an attached player. Host tests do not model electrical behavior or every interrupt/concurrency schedule.

| Version | Core bytes | SHA-256 |
| --- | ---: | --- |
| PB24 | 1995312 | `42e3028da6055ed2e582fe80354b4325d0cbb3ca34d14e6919bfc1b5a424cb42` |
| PB25 | 1995316 | `0890f3fdf594b45f42eba1bd7c9845147883eb947df21c37d146534a57d01f44` |
| PB26 | 1995448 | `d1f8eb6d25fd8ceed7b55b2031c0f5210e00f13a848c8cf45c66d9227531c7da` |

These identify locally tested candidates; firmware binaries, private installation scripts and personal evidence are not distributed here. Build your own core and matching codecs using [BUILD.md](BUILD.md).

## On-device results and limits

PB23 and PB24 follow-up tests still found changed data. Earlier repeated reads disagreed even through a direct card reader; bootloader USB controls also failed. This does not isolate one code or hardware root cause. An attempted Apple restore failed, so Apple-mode transfer reliability was not established by this work.

A replacement card passed a full-capacity write/read test through a separate reader, with zero reported lost, corrupt, changed or overwritten sectors. Initial formatting through its 512-byte reader view produced a layout that did not boot through the player’s 4096-byte USB view; recreating the approved layout through the player corrected booting. This was separate, explicitly authorized storage work, not a firmware update or bootloader patch.

PB25 booted on that card. A test song and two albums played normally; subsequent file hashes and filesystem checks passed. A Files-filter settings screen was initially mistaken for the actual browser. Enabling Files in the main-menu editor resolved that navigation issue without a browser-code patch.

PB26 installation verified all 42 core/info/codec files after remount while preserving settings. The Music database then built and persisted, and the two test albums appeared and played through Music. All 38 album files remained unchanged on reconnection; the filesystem check passed. This confirms the small-library bootstrap fix on the tested player, not full-library scaling or permanent storage reliability.

The larger restore remains **incomplete**. Completed batches passed remount hashes/filesystem checks; macOS login-window and indexing processes occasionally refused unmount before a scan could start. Normal retries allowed checks to proceed. Private transfer tooling retries only the specific pre-scan unmount refusal, never a real filesystem/checksum failure, and does not force unmount. At the user’s pause request, completed files in the partial batch also passed hashes, the unfinished temporary copy was removed, the filesystem check passed and the player was safely ejected.

Next acceptance is to resume with existing-file verification, finish all batches, perform full planned-library and firmware checks, then test database refresh, playback, idle/restart and reconnection. Headset controls, long-term battery behavior, comprehensive accessory support and corruption root cause remain unresolved. Do not infer sustained reliability from successful playback alone.
