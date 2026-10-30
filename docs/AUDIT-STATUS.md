# Ongoing code audit

Current checkpoint: **PB29**, updated 2026-10-30. This remains a partial, evidence-based review, not an every-line certification. [PB29](PB29-NAVIGATION.md) changes the regular Music/Now Playing Menu return and preserves [PB28's cleanup correction](PB28-ARTWORK-CLEANUP.md). The native PB29 build and installation-time firmware/artwork/filesystem checks passed; its restart and two Menu paths remain unconfirmed. The preceding PB28 build passed 47 host suites, and its first restart/reconnect was clean. The full PB27 restore and post-repair checksum pass completed; long-term storage acceptance remains open.

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
| Replaced artwork still held by a reader leaks clusters at unmount | PB28 routes reader teardown through deferred unlink cleanup; old callback fails the host regression and fixed callback passes. First hardware reconnect is clean; exact provenance of the earlier 13 orphans remains unproven. |
| Menu from Music-launched Now Playing always exits to the root | PB29 uses the saved regular Music origin; main-menu Now Playing still returns to the root. Native build and installation checks pass; physical Menu behavior pending. |
| Files menu appears to return without browsing | User was in the display-filter settings screen; enabling the actual Files menu resolved navigation. No browser-code fix was indicated. |
| Headset controls and unfinished station engine | Physical headset behavior remains unresolved; station engine is excluded, not shipped or certified. |

Earlier storage inconsistencies appeared through running firmware USB, bootloader USB and direct-reader repeated reads. No single corruption root cause has been proven. A replacement card passed full-capacity reader testing, and PB26 small-library playback/remount checks passed. Neither result establishes electrical health of the entire player or long-term write reliability.

Remaining work includes repeated artwork-cache activity, playback/shutdown/reconnection checks and longer USB integrity runs. Stop on real filesystem or checksum failures. macOS refusing an unmount before scanning is a separate host blocker, not a filesystem-corruption result. Native builds and mocks do not certify every theme, codec, accessory, concurrent schedule, battery behavior or power-loss scenario.
