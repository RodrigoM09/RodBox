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

Each checkpoint has a matching `checkpoints/<name>.json`. PB1–PB3 are validated artifact reconstructions; PB5 is explicitly rolled back. PB10 passed the user's restart/playback checks; PB11 analysis and hardware acceptance remain pending. See BUGS-AND-LESSONS.md for failure/rollback context and CREDITS.md for the imported/inherited code chain.
