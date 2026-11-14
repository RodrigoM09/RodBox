# RodBox project handoff — 2026-11-14

## Start here: current outcome and next task

**PB51 now plays digital USB audio in the user's 2015 Lexus ES350 factory stereo.** This is the user's report on 2026-11-14, not a new log-confirmed or filesystem-confirmed result. Preserve this working audio path. Do not restart the investigation from the assumption that Rockbox cannot provide digital USB audio: RodBox contains substantial custom iAP/USB work.

Remaining user-reported behavior:
- The head unit's song information updates when skipping forward/back within the album selected initially.
- Choosing a song from a different album or artist does not update the displayed information.
- Album artwork does not appear/update after changing songs.
- Do not infer a new audio failure from these display failures. Playback now works.

Next step: preserve fresh PB51 logs and check the filesystem read-only when the iPod is connected with Hold off. Compare within-album skip with cross-album/cross-artist selection, including the outgoing track-change notification, current track identity, selected database category/record state, metadata response and artwork requests. Determine whether notifications, database selection and artwork use stale album/queue-relative indices. This is an investigation hypothesis, not an established diagnosis. Keep the working USB audio driver unchanged unless evidence demands otherwise. The next firmware version would be PB52; none has been built yet.

## Hardware and user constraints

- Seventh-generation iPod Classic, previously recorded as MC297LL/A; Rockbox build target `ipod6g`, S5L8702, 64 MB. The target name does not identify the physical generation.
- iFlash Quad adapter; current card Samsung PRO Plus 256 GB, tested with a Unitek USB 3.0 Type-C reader before installation. Older 128 GB and 512 GB cards had separate tests/failures; never confuse them with the current card.
- 2015 Lexus ES350, factory stereo, 30-pin-to-USB cable.
- Mac host. Working directory is the user's `Documents/ChatGPT/IPOD`; source repository is its `rodbox-community` subdirectory. Source music has been on PhotoArchiv/Toshiba; discover the actual mounted source rather than assuming an old path.
- User repeatedly asks to conserve usage: focused reads/tests, concise progress, minimal delegation, no broad speculative rewrites or unnecessary full-library checks.
- Preserve music bytes, filenames, tags and album structure. Sidecar artist artwork was added separately. Do not embed or rewrite tags without fresh authorization.
- Formatting, repair, installation and transfers are separate operations. Past approvals are tied to their stated task; this handoff itself authorizes no new destructive operation. Device identifiers such as disk7 are ephemeral.
- Hold ON during connection/boot has repeatedly entered Apple firmware and rewritten the partition map, causing “no partition found.” Keep Hold OFF. Do not recommend an Apple restore or Disk Mode transfer casually; this layout has a known history of being rewritten.

## Repository and installed build

- Repository: https://github.com/RodrigoM09/RodBox
- Work/publish branch: `community`. `main` is the locked stable reference; do not merge experimental releases into main without explicit instruction.
- PB51 source commit: `d70811c`; tag `checkpoint/pb51`.
- PB50 source commit: `2b8533c`; tag `checkpoint/pb50`. PB49: `747c837`.
- Installed version: `rodbox-pb51-startup-wait-261113`.
- PB51 core SHA-256: `d34b646543322bb768ae0d0528aa250c3f5a6a22ff1aa7a94bbf4d0222c49e92`.
- Local artifacts: `prepared-pb51/rockbox.ipod`, `rockbox-info.txt`, `codecs/` (40 codecs), `SHA256.json`, `source-sha256.json`, `PB51-from-PB50.patch`, `RECOVERY-NOTES.md`.
- `PB51-build-verification.json` and `PB51-install-verification.json` are local authoritative build/install evidence. Public records are `checkpoints/pb51.json` and `checkpoints/pb51-source-sha256.json`.
- PB51 installation verified all 42 firmware files, backed up/verified 1,370 protected files, checked database structure, 86 artist images and 765 cached images. Filesystem passed; 2,243 music-folder file inventory/size/mtime records were unchanged. No full music checksum was repeated. Safely ejected after install on November 13.
- Current physical connection is not established by the November 14 playback report. Inspect it before device operations; do not assume it is still mounted.

## What PB51 changed and why it matters

PB50 captured three Lexus sessions, 28 retries and zero successful audio completions. The Lexus selected streaming alternate setting 1 and 44.1 kHz, and did not disable the music stream before the terminal failure. Initial recovery stopped after eight re-arms, about 10 ms in those traces, leaving the PCM batch pump stopped until explicit restart.

PB51 retains the SAME unsent initial packet while the endpoint remains active and busy, until delivery or stream cancellation. Recovery still waits for its service window and endpoint-disable acknowledgment. It does not pull fresh PCM for retries. It excludes consumed packets, established-stream failures, inactive endpoints and observed timeout/AHB errors. Counters/logs saturate at eight rather than growing indefinitely. A host that never polls can leave the initial packet pending; recovery continues at service-window cadence, not in a new busy-wait loop.

The regression fails on PB50 and passes on PB51 through 10,000 missed windows, including same-buffer retention, bounded logging/counters and error exclusions. All 30 USB test scripts and native build passed. Image checksum and 42 artifact hashes passed. The changed driver matched native build source; the complete unchanged source tree was not re-read because a bitmap read stalled. The previously fully verified PB50 tree was used as the incremental baseline. Report this limit honestly.

The user's successful Lexus audio test is strong practical progress, but it does not prove every sample rate, disconnect/reconnect, pause/resume, long playback or shutdown case. Do not claim all corruption or USB compatibility bugs are solved.

## Code map for the remaining display issues

Paths are relative to `rodbox-community`:
- `firmware-source/firmware/usbstack/usb_iap.c`: USB configuration, streaming interface and endpoint descriptors, iAP transport/initialization.
- `firmware-source/firmware/usbstack/iap/audio.c`: PCM sink, rate negotiation, per-track attributes, batching and sample sizes.
- `firmware-source/firmware/usbstack/iap/libiap/iap.c`: command dispatch, database/metadata responses, notifications and artwork transfers. Existing unsupported-type warnings refer to database category requests; do not assume they are audio errors.
- `firmware-source/apps-ipod/iap/`: platform/library integration. Search for `iap_platform_get_db_count`, selection, current-track ID, notification and artwork callbacks to find the exact implementations.
- `firmware-source/firmware/usbstack/usb_core.c`: transfer batching/completion ownership and control transactions.
- `firmware-source/firmware/drivers/usb-designware.c`: controller scheduling/recovery; PB51 working-audio change is here.
- `firmware-source/apps-ipod/system/usb_log_file.c`: persistent log formatting, allocation/write handling.
- `tests/usb/test_iap_track_notification.py`, `test_iap_filtered_metadata.py`, `test_iap_track_info_layout.py`, `test_iap_metadata.py`, `test_iap_artwork_times.py`, `test_iap_control_reports.py`: useful focused starting points. Inspect actual tests before extending them.
- `tests/usb/test_iso_recovery.py`: PB51 regression; keep it passing.

For display fixes, test actual production code and binary response layouts. Include transitions across albums/artists and queues, metadata indices versus selected database indices, artwork request identity, valid empty/unsupported responses, and notification subscriptions. Do not mark an issue fixed merely because host tests pass; the Lexus supplies the acceptance test.

## Logs, evidence and filesystem safety

Device logs are under **`/Volumes/IPOD/.rockbox/logs/`**, NOT directly under `.rockbox`: `usb-audio.log`, `usb.log`, `usb.1.log`. Preserve copies and hashes on the Mac before changes. Logs contain older firmware sessions; split by version headers and identify actual Lexus configuration 2 sessions. Configuration 1 is generally the Mac storage session. The iPod clock has been unset; header dates and cumulative timestamps are not reliable calendar dates.

Persistent override in `.rockbox/fixed.cfg`:
```
debug log usb: on
debug log expiry: never
```
Preserve it for testing. USB mode Mass Storage was used for Mac access while custom accessory handling selects the Lexus configuration. Do not randomly change VID/PID, descriptors or mode settings now that sound works.

Local PB50 evidence: directory named in `PB50-latest-evidence.txt`, containing hashed logs, `filesystem.log` and `verification.json`. PB49 evidence similarly uses `PB49-latest-evidence.txt`. PB49 had two orphaned clusters, subsequently repaired with approval. PB50's latest read-only filesystem check passed with no orphan clusters or cross-links. PB51's installation check also passed. No post-Lexus PB51 filesystem/log check has yet been done in this handoff task.

Use existing guarded helpers as reviewed references, not blindly:
- `repair_approved_pb29_fseventsd.py`: `guard`, `check`, `music_stats`, cache checks. Guard validates the known volume identity, block size, offset, parent size/media and writable state. Its historical repair routine is NOT a generic authorization to repair.
- `install_approved_pb51.py`: identity check, transfer lock, preflight filesystem verification, source/installed hashes, protected backup, staging/replacement, postflight checks and safe eject. Adapt only for an explicitly approved install.
- `PB26-music-transfer.lock`: shared exclusive lock used by device operations.
- `PB50-before-PB51-20261113-105042`: local pre-install backup.

The card's intended FAT filesystem begins at byte 1,048,576 with 4096-byte sectors. Prior Apple-path partition rewrites pointed to 67,624,960 instead; the real FAT boot sector survived at the original offset. Existing partition inspection/correction scripts contain identity guards. Never copy old raw disk numbers or repair offsets without a new read-only inspection. Never run `repairDisk` solely because diskutil notes unused whole-disk space.

Size/mtime/inventory checks prove no observed structural change, not full music-byte integrity. A clean FAT check proves filesystem structure, not that every song matches its source. Do not conflate these claims.

## Build, test and publish workflow

The last native build used `/private/tmp/rodbox-pb42-source/firmware-source` and `/private/tmp/rodbox-pb42-build`; these historical directory names do not indicate the build version. Toolchain alias `/private/tmp/rodbox-arm-toolchain` points to the persistent Arm GNU 13.2.Rel1 toolchain under the IPOD workspace. Temporary paths may disappear; verify them first. Sync only intended source changes into the native tree.

Example native command, after setting a new explicit version:
```
PATH=/private/tmp/rodbox-arm-toolchain/bin:/usr/bin:/bin:/usr/sbin:/sbin make -C /private/tmp/rodbox-pb42-build -j4 VERSION=<new-version> bin codecs
```
Run relevant tests under `/usr/bin/python3`; the USB suite is `tests/usb/test_*.py`. ASan/UBSan regressions use clang. Use failing-before/passing-after cases where feasible. Package the core, info file and 40 codecs with codec paths under `codecs/`, not the artifact root. Verify image target `ip6g`, big-endian leading checksum `(sum(image[8:])+71) & 0xffffffff`, version and SHA-256 manifest.

Keep checkpoint JSON, source hashes, README current status, per-build notes, HISTORY, TESTING and VERIFICATION updated. Commit/push to community and checkpoint tag. Do not publish raw logs, personal device identifiers, backups or copyrighted music/art. Do not add files indiscriminately: eight pre-existing `* 2.*` duplicate source copies have historically been untracked and excluded from builds/publication. Inspect differences and retain them locally unless intentionally reconciled; they are not automatically the newest source.

## Preserved improvements and earlier investigations

RodBox integrates Rockbox, PodBox and selected RockPod ideas; preserve credits and licensing. It is the user's custom firmware, not a request to replace it with stock Rockbox.

Preserve the native Scrim/library/audiobook features, headset improvements, artwork sidecars/cache, database uniqueness and Album Artist grouping, Music and Now Playing return paths, analysis startup error handling, battery percentage continuity, storage/USB/FAT protections and all later iAP work. The database menu now groups Bad Bunny/Maluma by Album Artist. The earlier “Files > Music/All/Supported/Playlists” confusion was a file-filter settings screen; the actual Files entry had been hidden. Do not diagnose this historical UI issue as filesystem loss again.

Earlier storage failures occurred both through firmware and bootloader USB, and repeated direct-reader raw reads of an old card disagreed. That evidence did not isolate all failures to Rockbox. Replacement card/reader testing and later FAT/cache fixes improved reliability. Headset-control acceptance, battery calibration, old unexplained shutdowns and comprehensive analysis acceptance have not all been conclusively closed. Consult the checkpoint's evidence rather than generalizing from normal playback.

The following chronology and document index preserve the project's full recorded progression. Historical “built only” and “pending” statements describe their publication time; the current PB51 installation and user audio result above supersede those particular statuses.

## Recorded checkpoint chronology

# Source checkpoint history

All publication commits are new sanitized exports, not fabricated original commits. Every PB version has its own commit/tag. Raw private backups remain offline.

| Checkpoint | What changed | Evidence quality |
| --- | --- | --- |
| legacy-official-release | Record official Rockbox release baseline | firmware-evidence-only |
| legacy-folders-shortcuts | Record separate Music and Audiobooks browse shortcuts | generic-configuration-example |
| legacy-daily | Record pinned Rockbox daily lineage | upstream-reference |
| legacy-remote1 | Archive initial headset decoder correction | partial-historical-evidence |
| legacy-remote2 | Record second headset decoder iteration | partial-historical-evidence |
| legacy-remote-trace | Record trace-assisted headset diagnosis | partial-historical-evidence |
| legacy-remote3 | Preserve trace-informed remote3 source | preserved-source-export |
| legacy-main-menu | Archive initial folder-based main-menu patch | partial-historical-evidence |
| legacy-library-bookmark | Preserve database Music and latest-only bookmark source | preserved-source-export |
| legacy-rockpod-integration | Archive selected RockPod Cover Flow and flash changes | partial-historical-evidence |
| legacy-menu2 | Preserve legacy Update Now menu and storage integration | preserved-source-export |
| legacy-scrim-classic | Archive temporary Scrim Classic appearance adaptation | theme-export |
| podbox-upstream | Import pinned PodBox foundation with inherited credits | pinned-upstream-source-export |
| pb1 | Migrate to PodBox, native Scrim, library and audiobook features | artifact-based-reconstruction |
| pb2 | Add decoder-based multi-click actions and portrait lookup | artifact-based-reconstruction |
| pb3 | Normalize art-cache volume keys and refine the library menu | artifact-based-reconstruction |
| pb3-followup | Add missing icons and preserve corrected artwork presentation | artifact-based-reconstruction |
| pb4 | Add bounded artist-art fallback and RodBox title | verified-source-archive-export |
| pb5 | Try USB endpoint validation (later rolled back) | exact-saved-step-delta-rolled-back |
| pb5-rollback | Restore verified PB4 after supported filesystem recovery | verified-recovery-source-export |
| pb6 | Start a fresh music queue for explicit Shuffle Songs | exact-saved-step-delta |
| pb7 | Report unexpected USB write lengths as failed commands | exact-cumulative-step-export |
| pb8 | Reintroduce endpoint guards after accepted PB7 | exact-cumulative-step-export |
| pb9 | Reject invalid playlist insertion positions | exact-cumulative-step-export |
| pb10 | Move paired playlist index tails as overlapping-safe blocks | exact-cumulative-step-export |
| pb11 | Correct quiet/stereo energy, tempo-lock lifetime and sample duration; add Analyze Music Now and revision-aware refresh | native-build-and-synthetic-tests; device acceptance pending |
| pb12 | Use external-power presence for analysis; show battery/charging/USB state and Scrim analysis icon | native build, seven power cases and skin-parser checks; device acceptance pending |
| pb13 | Select battery icon, percentage or both; retain USB footer and include analysis waveform icon | native build, skin parser and font-geometry checks; device mode/layout acceptance pending |
| pb14 | Request a normal screen wake on external-power connection; align Now Playing battery top-right and place playback before maintenance actions | installed with verified before/after backups; native build and 15 host input-state checks passed; physical wake and post-restart checks pending |
| pb15 | Clear stale theme battery/clock pixels from the USB header before drawing one indicator | installed with verified before/after recovery checkpoints; native build and 24 actual-renderer framebuffer cases passed; physical acceptance pending |
| pb16 | Keep USB storage awake, recheck idle policy under the ATA lock and return failed wakes before transfer I/O | native build and 132 host scenario/configuration executions passed; installed/backed up and booted; small USB probe/readbacks passed, next write failed; sustained reliability unresolved |
| pb17 | Release ATA reset locks on power-up failure | prepared, not installed; native build and 220 actual-function scenario/configuration executions passed |
| pb18 | Preserve previous library/index files after failed final flush or close | prepared, not installed; native build and actual-function fault-injection tests passed |
| pb19 | Invalidate partial-sector cache before full writes and after failed writes | prepared, not installed; native build, actual-code coherence/error regressions and 40,000 mixed operations passed; device applicability unconfirmed |
| pb20 | Harden USB/FAT/ATA failures, checked library/artwork publication and worker handoff | native build and 41 host suites passed; hardware corruption remained |
| pb21 | Serialize iPod USB receive/storage DMA and verify write payloads | native build and 11 USB suites passed; hardware corruption remained |
| pb22 | Wait for ATA command/device-select status to settle | native build and 21 focused suites passed; second large transfer batch failed |
| pb23 | Make verified USB writes write-through before readback/success | native build and host suites passed; later bulk tests still found changed data, including a bootloader USB control |
| pb24 | Recognize iFlash ATA models and retain adapter power in non-PM idle sleep | native build and 44 host suites passed; installed and booted, later data reads remained inconsistent |
| pb25 | Preserve an active non-control DesignWare request when a second submission arrives | native build and 44 host suites passed; installed on a replacement card; song/two-album playback and later hashes passed |
| pb26 | Reclaim playback-owned memory for initial Music database commits, preserving playback headroom | native build and 45 host suites passed; on-device Music database and two-album playback confirmed; verified bulk restore paused by user, full acceptance incomplete |
| pb27 | Word-align database merge allocations for valid duplicate-name CRC accesses | native build and 46 host suites passed; installed, unique artist display confirmed, post-startup firmware/database/filesystem checks passed; full restore and later full post-repair checks passed; subsequent cache-related orphan clusters led to PB28 |
| pb28 | Close read-only streams through deferred unlink cleanup at USB/volume unmount | native build and 47 host suites passed; installed and booted; first reconnect passed firmware/artwork/filesystem with no orphan clusters; sustained acceptance open |
| pb29 | Return from Now Playing to the saved regular Music song list; keep main-menu Now Playing's return at the root | native build and install/remount firmware/artwork/filesystem checks passed; PB28 cleanup retained; PB29 startup and both Menu paths confirmed; later diagnostic-report cross-links led to PB30 |

| pb30 | Preserve FAT directory end markers so stale deleted entries stay hidden | old-code reproduction fails; eight focused suites/native build pass; existing duplicates repaired; user playback/artwork/shutdown/restart and clean reconnect passed |

Each checkpoint has a matching `checkpoints/<name>.json`. PB1–PB3 are validated artifact reconstructions; PB5 is explicitly rolled back. PB10 passed the user's restart/playback checks; PB11 analysis and hardware acceptance remain pending. See BUGS-AND-LESSONS.md for failure/rollback context and CREDITS.md for the imported/inherited code chain.

## PB31 — 2026-10-31

Stop and report analysis worker startup failures; retain startup error messages and distinguish index memory failures. Three focused suites, native build and installation checks passed. Hardware analysis acceptance pending. See [PB31](PB31-ANALYSIS.md).

## PB32 — 2026-10-31

Classic battery percentage continuity across charging/discharging curves. User transition test and reconnect checks passed; calibration and prior shutdown cause remain unresolved. See [PB32](PB32-BATTERY.md).

## PB33–PB35: Lexus interoperability

PB33 enlarges the bounded iAP control buffer to match advertised reports.
PB34 dispatches complete checksum-valid frames and confirms authentication.
PB35 defers playback acknowledgements to state changes and fixes rate-list EOF
parsing. Native builds and focused tests passed. Lexus still has no audio or
advancing timer; metadata/artwork command support is incomplete. See
[the current investigation](PB35-LEXUS-PROTOCOL.md). Main remains unchanged.

## PB36–PB40: audio transport and metadata follow-up

- PB36: ISO failure recovery and metadata/artwork handlers; the car test exposed noise and accelerated playback.
- PB37: stop consuming PCM after failed or short transfers; silence remained.
- PB38: host-token synchronization and missing-tag display fallbacks; nonempty metadata replies observed, audio unresolved.
- PB39: service-window checks, artwork-independent track notifications and separate audio logs; diagnostics confirmed stalled startup and failed restart. Filesystem clean.
- PB40: cancel the pending audio endpoint on stop, permit restart after failure, serialize/coalesce rate requests, correlate acknowledgements and unify timeout cleanup. Installed and verified; in-car acceptance pending.

Each checkpoint was reconstructed from its saved cumulative patch and matched to recorded source hashes before publication. The ten focused PB40 suites were rerun on the restored checkout. Native compilation and installation results are from the original build/install records, not new device tests.

## PB41–PB42

PB41 corrects root-level artwork paths in the companion health report and permits an explicit compiler for playlist harnesses. Seven health tests, 21 guard cases and 50,000 differential cases passed.

PB42 addresses the PB40 trace in which endpoint 81 waited indefinitely with EPENA clear. The S5L8702 first packet is now armed directly; other targets retain token synchronization. Eleven focused suites passed, including a startup regression that fails on PB40. The native core and 40 codecs built and passed image/source/hash verification. Lexus playback acceptance remains pending.

## PB43

PB42 hardware testing recorded three immediate zero-byte failures and no successful audio completions; its filesystem remained clean. PB43 adds bounded same-buffer startup recovery after endpoint-disable acknowledgement, alternates timing parity, clears stale disable state, and anchors subsequent scheduling to successful completion. Partial transfers and established-stream errors retain fail-stop behavior. Lexus acceptance remains pending.

## PB44

PB43 hardware testing still showed no audio completions or retries and found excess usb.log allocation. PB44 corrects retry eligibility to use unsent packet count, records the raw register, and commits/reconciles USB diagnostic files before consuming ring entries. Built and tested only; hardware acceptance pending.

## PB45

PB44 hardware retries activated but exhausted before the final host rate command; filesystem passed. PB45 restarts an enabled failed pump on matching SET_CUR and gives each explicit restart a fresh endpoint priming budget. Busy Play/Pause requests are deferred with bounded acknowledgement instead of rejected as assertions. Built only; hardware acceptance pending.

## PB46

PB45 still had no successful audio completions; filesystem passed. PB46 replaces the mismatched 1024-byte iAP endpoint allocation with the same 192-byte constant used by its descriptor and buffers. Built only; hardware acceptance pending.

## PB47

PB46 confirmed 192-byte packets but no audio completions. PB47 retains each initial high-speed packet for the advertised eight-microframe polling interval before bounded recovery. Established/full-speed timing is unchanged. Built only; hardware acceptance pending.

## PB48

PB47 still recorded no audio completions despite the extended window; filesystem passed. PB48 explicitly declares synchronous ISO audio to match its host-paced packet source and records bounded raw endpoint interrupt indications. Built only; hardware acceptance pending.

## PB49

PB48 exposed exhausted state surviving idle endpoint reset and disable/NAK-effective events consuming the IRQ log budget. PB49 resets active ISO IN priming state on explicit idle/busy resets and separates token diagnostics from completion/error logs. Built only; hardware acceptance pending.

## PB50

PB49 recorded zero audio completions across 36 retries. PB50 captures successful stream alternate settings and bounded endpoint/mask/frame snapshots before recovery. Scheduling is unchanged; this is a diagnostic build, not a confirmed fix. The separately approved two-orphan repair passed without formatting or music writes.

## PB51

PB50 still produced no audio. PB51 removes the eight-attempt terminal startup failure for the same unsent first packet, while preserving stream cancellation, error exclusions and bounded logging. Host readiness delay is a hypothesis; Lexus playback is unverified. No device writes or installation.


## Further project records

- `AI-ASSISTANCE.md` (repository: `docs/AI-ASSISTANCE.md`)
- `AUDIT-STATUS.md` (repository: `docs/AUDIT-STATUS.md`)
- `BATTERY-DISPLAY.md` (repository: `docs/BATTERY-DISPLAY.md`)
- `BUGS-AND-LESSONS.md` (repository: `docs/BUGS-AND-LESSONS.md`)
- `BUILD.md` (repository: `docs/BUILD.md`)
- `FILESYSTEM-RECOVERY.md` (repository: `docs/FILESYSTEM-RECOVERY.md`)
- `HISTORY.md` (repository: `docs/HISTORY.md`)
- `NATIVE-ANALYSIS.md` (repository: `docs/NATIVE-ANALYSIS.md`)
- `PB20-PB23-DURABILITY.md` (repository: `docs/PB20-PB23-DURABILITY.md`)
- `PB24-PB26-STATUS.md` (repository: `docs/PB24-PB26-STATUS.md`)
- `PB27-DATABASE-UNIQUENESS.md` (repository: `docs/PB27-DATABASE-UNIQUENESS.md`)
- `PB28-ARTWORK-CLEANUP.md` (repository: `docs/PB28-ARTWORK-CLEANUP.md`)
- `PB29-NAVIGATION.md` (repository: `docs/PB29-NAVIGATION.md`)
- `PB30-DIRECTORY-END.md` (repository: `docs/PB30-DIRECTORY-END.md`)
- `PB31-ANALYSIS.md` (repository: `docs/PB31-ANALYSIS.md`)
- `PB32-BATTERY.md` (repository: `docs/PB32-BATTERY.md`)
- `PB33-CONTROL-REPORTS.md` (repository: `docs/PB33-CONTROL-REPORTS.md`)
- `PB34-HID-FRAMES.md` (repository: `docs/PB34-HID-FRAMES.md`)
- `PB35-LEXUS-PROTOCOL.md` (repository: `docs/PB35-LEXUS-PROTOCOL.md`)
- `PB36-LEXUS.md` (repository: `docs/PB36-LEXUS.md`)
- `PB37-LEXUS.md` (repository: `docs/PB37-LEXUS.md`)
- `PB38-LEXUS.md` (repository: `docs/PB38-LEXUS.md`)
- `PB39-LEXUS.md` (repository: `docs/PB39-LEXUS.md`)
- `PB40-LEXUS.md` (repository: `docs/PB40-LEXUS.md`)
- `PB41-COMPANION.md` (repository: `docs/PB41-COMPANION.md`)
- `PB42-FIRST-TRANSFER.md` (repository: `docs/PB42-FIRST-TRANSFER.md`)
- `PB43-bounded-first-packet.md` (repository: `docs/PB43-bounded-first-packet.md`)
- `PB44-RETRY-LOG.md` (repository: `docs/PB44-RETRY-LOG.md`)
- `PB45-HOST-RESTART.md` (repository: `docs/PB45-HOST-RESTART.md`)
- `PB46-PACKET-SIZE.md` (repository: `docs/PB46-PACKET-SIZE.md`)
- `PB47-SERVICE-WINDOW.md` (repository: `docs/PB47-SERVICE-WINDOW.md`)
- `PB48-AUDIO-SYNC.md` (repository: `docs/PB48-AUDIO-SYNC.md`)
- `PB49-RETRY-RESET.md` (repository: `docs/PB49-RETRY-RESET.md`)
- `PB50-AUDIO-PROBE.md` (repository: `docs/PB50-AUDIO-PROBE.md`)
- `PB51-STARTUP-WAIT.md` (repository: `docs/PB51-STARTUP-WAIT.md`)
- `PLUG-IN-WAKE.md` (repository: `docs/PLUG-IN-WAKE.md`)
- `POWER-AND-BATTERY.md` (repository: `docs/POWER-AND-BATTERY.md`)
- `RECOVERY.md` (repository: `docs/RECOVERY.md`)
- `RESET-LOCKS.md` (repository: `docs/RESET-LOCKS.md`)
- `SAFE-LIBRARY-FINISH.md` (repository: `docs/SAFE-LIBRARY-FINISH.md`)
- `SECTOR-CACHE.md` (repository: `docs/SECTOR-CACHE.md`)
- `TESTING.md` (repository: `docs/TESTING.md`)
- `USB-HEADER.md` (repository: `docs/USB-HEADER.md`)
- `USB-STORAGE-AWAKE.md` (repository: `docs/USB-STORAGE-AWAKE.md`)

Also consult `README.md`, `CREDITS.md`, `CONTRIBUTING.md`, all `checkpoints/*.json`, and local verification reports/artifacts. This handoff summarizes the recorded context and links the detailed record; it is not a substitute for raw evidence or a claim that every historical hypothesis was proven.
