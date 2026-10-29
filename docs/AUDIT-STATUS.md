# Ongoing code audit

Current checkpoint: **PB27**, updated 2026-10-29. This is a partial, evidence-based review, not a completed every-line audit. See [PB27 database uniqueness and limits](PB27-DATABASE-UNIQUENESS.md), [PB24–PB26 history](PB24-PB26-STATUS.md) and [PB20–PB23 durability work](PB20-PB23-DURABILITY.md). All 46 cumulative host suites and the native PB27 build passed. PB27 is installed; normal startup and unique artist display were confirmed by the user, followed by matching firmware, consistent database reads and a clean filesystem check. The verified music restore has resumed; full transfer and long-term acceptance remain incomplete.

| Finding | Current evidence and state |
| --- | --- |
| Stale ATA partial-sector cache | PB19 invalidation is retained; actual-code coherence/error/mixed-operation tests pass. Not established as the sole physical corruption cause. |
| ATA reset errors retaining recursive mutex | PB17 unlock corrections retained and host-tested. |
| Library/index publication after late errors | PB18/PB20 checked writes, flushes and closes retained; failure-injection tests pass. |
| USB command/error/reset and geometry handling | PB20 bounds, failure draining, reset handling and flush propagation retained; source-body mocks pass. |
| Overlap between USB receiving and storage verification | PB21 serializes writes/readback; PB23 flushes before verification/success. Earlier hardware mismatches continued. |
| ATA stale status after command/select | PB22 status-settling correction retained and regression-tested. |
| Non-PM adapter power handling and detection | PB24 retains idle power and recognizes iFlash ATA models; mocks pass, physical root cause unproven. |
| Busy non-control endpoint request replacement | PB25 refuses the overlapping request while preserving EP0 behavior; regression passes. |
| Analysis working-file errors and background handoff | PB20 checked error paths and worker quiescence retained; mocked lifecycle/error tests pass. |
| Initial Music database cannot reclaim playback-owned memory | PB26 bounded allocation/shrink correction; regression and on-device database/Music playback checks pass. |
| Database merge buffer can misalign duplicate-name CRC word accesses | PB27 aligns both allocation paths and bounds rounding overflow; actual allocator/insertion regression reproduces PB26’s invalid access and passes after correction. Existing duplicate records were separately deduplicated with all track fields preserved. |
| Files menu appears to return without browsing | User was in the display-filter settings screen; enabling the actual Files menu resolved navigation. No browser-code fix was indicated. |
| Headset controls and unfinished station engine | Physical headset behavior remains unresolved; station engine is excluded, not shipped or certified. |

Earlier storage inconsistencies appeared through running firmware USB, bootloader USB and direct-reader repeated reads. No single corruption root cause has been proven. A replacement card passed full-capacity reader testing, and PB26 small-library playback/remount checks passed. Neither result establishes electrical health of the entire player or long-term write reliability.

Remaining work includes completing the active verified library restore and post-transfer database/playback/reconnection checks. Stop on real filesystem or checksum failures. macOS refusing an unmount before scanning is a separate host blocker, not evidence that a scan found corruption. Native builds and mocks do not certify every theme, codec, accessory, concurrent schedule, battery behavior or power-loss scenario.
