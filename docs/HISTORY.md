# Source checkpoint history

All publication commits are new sanitized exports, not fabricated original commits. Published PB checkpoints have their own commit/tag; PB53 was an interim local build recorded retrospectively with an exact source delta, not a fabricated historical tag. Raw private backups remain offline.

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

## PB51 hardware update — 2026-11-14

User confirms Lexus USB audio playback now works. Cross-album/artist metadata and changed-track artwork remain unresolved. Installation was verified; post-Lexus logs/filesystem have not yet been checked. See HANDOFF.md for continuation context.

## PB52

Announce completed replacement queues before playback and send queue-contents notifications before reused track indices. Refresh per-track artwork capabilities on the USB tick, including ExtendedInterface capability-change events. Convert selected display-relative indices to the same rotated queue positions used by metadata and artwork. PB51's working USB audio driver, PCM path, descriptors and codecs are unchanged. Three new production-source ASan/UBSan regressions failed before and pass after; all 33 USB scripts and the native build pass. Installed with a verified PB51 backup; all 42 firmware files, 1,372 protected files and pre/post filesystem checks passed. Music inventory/size/mtime unchanged for 2,243 files; no full music checksum repeated. Safely ejected. Lexus acceptance remains pending. See PB52-TRACK-REFRESH.md.

## PB53 — interim local build

Prioritize finite track/artwork events before continuously reasserted elapsed time. The production asynchronous HID regression failed before the change and passed after; 34 USB scripts and the native build passed. It was installed with protected-data/music checks and safe ejection. Subsequent user testing still found stale Lexus metadata on natural/iPod skips. PB53 was not separately published; its original changed C snapshot and preserved regression are reproducible from PB52 using `checkpoints/pb53-source.patch`, with a retrospective record in `checkpoints/pb53.json`.

## PB54

PB54 (`rodbox-pb54-track-sync-261115`) is built, installed, read-back verified and safely ejected. All **36 USB scripts** pass, including production-source buffered-snapshot and current-track reconciliation tests under ASan/UBSan. Independent follow-up review passed after rejecting a fallback-I/O accessor before installation. USB-side identity reconciliation covers missed playback callbacks and full-path changes at reused queue indices/counts, with buffered-only metadata access and reconnect invalidation. The working PCM/controller/descriptors/playback implementation and all 40 codecs remain unchanged. **Actual Lexus metadata/artwork and continued audio acceptance remain pending.**

Installation verified all 42 firmware files; only core/info changed. 1,370 protected files were backed up and verified, database structures and 765 cache-image structures passed, and pre/post read-only filesystem checks passed. Inventory/size/mtime stayed unchanged for 2,243 music files; no music writes, repairs, formatting or repeated full-content scan. Private recovery backup: `PB53-before-PB54-20261115-095707`. Image SHA-256: `3a2a18cd95b50a6d4ce5fa68fdc32b7367288da505338e5eecd0f6cf1b2066d7`. The initial candidate was rejected before installation for possible playlist/tagcache lookup I/O; the final candidate uses the already-existing buffered-only accessor, checks stop during copy, and resets identity at reconnect. The exact Lexus subscription mask and missing-callback cause remain unproven. See PB54-TRACK-SYNC.md.

## PB54 user result / PB55

User reports PB54 retains the skip-refresh issue. Natural song completion was not retested; its physical result is unknown. Newly retained startup logs contain the actual Lexus masks in two sessions and expose the missing UID/caps mapping and absent UID sender. Earlier index-based host tests did not exercise these actual subscriptions.

PB55 (`rodbox-pb55-lexus-uid-261115`) is built, installed, read-back verified and safely ejected. All **37 USB scripts** pass, including a captured Lexus subscription replay under ASan/UBSan with production decoding, UID/caps notifications, canonical path keys and asynchronous HID completion. Independent code review passed. **Physical PB55 Lexus acceptance remains pending; song completion was not retested on PB54.**

The retained PB54 startup trace now proves the Lexus requests DisplayRemote `0x0000018d` and ExtendedInterface `0x00000901`: UID/capability events, not index events. The old request mapper dropped both requested bits and there was no UID sender. PB55 decodes them, sends the existing stable metadata UID as type `0x0A` plus eight big-endian bytes, and includes UID-only subscriptions in buffered reconciliation. No subscription is forced or music/key algorithm changed.

All 42 firmware files read-back verified; only core/info replaced. 1,370 protected files backed up and verified; database and 765 cache-image structures passed; pre/post filesystem checks passed. 2,243 music entries retained inventory/size/mtime. No music writes, full-content rescan, repairs or formatting. All 40 codecs and working audio/controller/PCM/descriptors/playback sources are unchanged. Private PB54 recovery backup: `PB54-before-PB55-20261115-103146`. Core SHA-256: `fbd1b155e6b3a8d9cb91877214b72608b96ef1912cce2ae2146bb6d52fac7920`. See PB55-LEXUS-UID.md.
