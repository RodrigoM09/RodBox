# Ongoing code audit

Current checkpoint: **PB26**, updated 2026-10-29. This is a partial, evidence-based review, not a completed every-line audit. See [PB24–PB26 evidence and remaining limits](PB24-PB26-STATUS.md) and [PB20–PB23 durability work](PB20-PB23-DURABILITY.md). All 45 cumulative host suites passed again; native candidates built, and PB26 is installed and booted. The Music database bootstrap fix is confirmed on the tested player. Bulk transfer acceptance remains incomplete and was paused by the user after verification and safe eject.

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
| Files menu appears to return without browsing | User was in the display-filter settings screen; enabling the actual Files menu resolved navigation. No browser-code fix was indicated. |
| Headset controls and unfinished station engine | Physical headset behavior remains unresolved; station engine is excluded, not shipped or certified. |

Earlier storage inconsistencies appeared through running firmware USB, bootloader USB and direct-reader repeated reads. No single corruption root cause has been proven. A replacement card passed full-capacity reader testing, and PB26 small-library playback/remount checks passed. Neither result establishes electrical health of the entire player or long-term write reliability.

Remaining work includes completing the paused verified library restore and post-transfer database/playback/reconnection checks. Stop on real filesystem or checksum failures. macOS refusing an unmount before scanning is a separate host blocker, not evidence that a scan found corruption. Native builds and mocks do not certify every theme, codec, accessory, concurrent schedule, battery behavior or power-loss scenario.
