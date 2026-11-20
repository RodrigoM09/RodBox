# PB56 — experimental audio/reliability test candidate

`rodbox-pb56-audio-test-261117`, ipod6g / S5L8702 / 64 MB, based on the accepted PB55 firmware and its follow-up documentation at source commit `2a21f02582e127abcc21f83a4db594ec586188f4`. PB56 is an **installed, readback-verified experimental build**. `checkpoint/pb56` is a source-only checkpoint; no binary or personal device evidence is distributed. PB55 remains the last user-accepted rollback.

## Included

1. **iAP rate fallback:** an ignored late SET_CUR for the previous rate no longer marks the current rate as accepted and disables fallback. Production announcement, ACK/timeout/refusal and PCM silence gates are exercised.
2. **Shared analog output reliability:** remove the music-channel-only CS42L55 powerdown/wake calls. Voice/beep and other mixer users are no longer silenced by a music stop. Normal codec init/close controls power; reintroducing shared idle savings is deferred rather than adding I2C or sleep to a DMA interrupt. **Idle power/battery cost may increase and is not measured.**
3. **Tone headroom:** preserve full compensating attenuation for CS42L55 bass/treble boosts, capping analog compensation instead of surrendering headroom. Boosted output may be quieter near the volume ceiling. Neutral gain, mute, balance, unity lineout and other-codec/simulator/mono guards retain their established behavior.
4. **Finite iAP notification fairness:** play/power/shuffle/repeat/stopped/extended status drain before recurring time traffic, without undoing queue/UID/artwork ordering or subscription gating.
5. **Generic USB-host DAC gain:** choose a supported unity-or-lower control value, rounded down to its advertised gain grid; read back changes. Unknown/failed/malformed/multi-range controls are left unchanged. This is separate from Lexus iAP and does not establish physical loudness safety for every DAC.

## Explicitly not included

- **New anti-alias resampler:** actual portable production C vectors reproduce the existing alias-rejection limitation. Added host characterization, native-rate sample identity and mono/stereo chunk-continuity checks. `--require-bandlimit` intentionally remains a failing future acceptance gate. No experimental filter is secretly enabled; ARM performance and device battery/response validation are absent.
- **Automatic established-stream retry:** existing stop-on-failure safeguards remain, preventing runaway PCM consumption and replay of potentially delivered audio. A delivery-aware USB-thread recovery design is deferred.
- **Queued PCM rebuild during different-rate sink switching:** requires an integrated reproduction before flushing/discarding samples; no speculative rate-handover change.
- **Generic asynchronous feedback expansion:** UAC1 and split/hub limitations remain; no unsupported clocking compatibility claim.
- **Cirrus/PLL/hidden-register tuning, blanket treble EQ or 75ms warm-wake delay:** not justified by measurements of this player. PB56 does not claim to cure the historical analog treble/IMD/phase allegations.

The nine findings are tracked individually in the private `scope-disposition.json`; deferred work is not represented as implemented.

## Verified host/build evidence

- The entire pinned physical baseline matched **12,299 Git blob hashes**, including all 15 previously recorded PB55 source snapshots; the original PB55 core hash was preserved.
- Fresh immutable PB55 baseline: **75 cumulative suites passed**.
- PB56 candidate: **81 cumulative suites passed**, plus **40 USB scripts** explicitly rerun and passed.
- New C harnesses use ASan/UBSan. The headroom matrix additionally covers 18,688 boost/volume combinations and legacy/simulator/mono guards.
- Native `make -j4 VERSION=rodbox-pb56-audio-test-261117 bin codecs` returned 0. All 12,042 tracked firmware-source file hashes were unchanged during the build.
- Five compiler/linker warnings were emitted in unchanged Mikey/plugin/linker areas; this is not a warning-free build. Configure also warned that 13.2.1 differs from its recommended 9.5.0; the verified Arm GNU 13.2.Rel1 toolchain was used.
- Independent code review passed with no concrete correctness/security regression found. Package verification is recorded in the private build report; native build success alone is not physical acceptance.

These tests do not establish physical noise, THD/IMD, phase response, bit-perfect output, battery life, every USB DAC/hub combination or in-car acceptance. The resampler vectors exercise portable production C, not execution of the ARM assembly path.

## Installation/acceptance

On 2026-11-19, an initial read-only FAT check found one orphaned cluster and blocked installation before writes. A separately approved volume-only repair cleared it after a verified protected backup. The orphan's unknown contents were not preserved; no formatting or partition-map repair was performed. A fresh guarded installation then read back all 42 firmware files. Only `rockbox.ipod` and `rockbox-info.txt` changed; the 40 codecs match PB55. The pre/post FAT checks were clean, PB55 rollback was preserved, and the iPod was safely ejected. The firmware installation made no music writes; 2,216 existing music-tree files matched in inventory, sizes and modification times (not a full byte check).

Subsequent library operations added 291 validated tracks and 18 album images, then 23 artist portrait sidecars for 11 artists. The existing library files were not overwritten. Artist portraits are separate from album covers and use `.artist/folder.jpg` alongside the album/disc. The portrait install left the cache and database unchanged. To refresh the Artists list, run **Settings → Library → Maintenance → Update Art Cache** after the database knows the new tracks. Physical display confirmation is pending.

For physical acceptance, test at a low listening level: ordinary 3.5 mm playback, music stop followed by voice/beep, neutral and boosted gain behavior, Lexus local/remote skips and natural completion, artwork across albums/artists, pause/reconnect and mixed 44.1/48 kHz content. Use dummy loads and appropriate measurement hardware—not ears—for full-level test tones. The known resampling limitation is not an expected PB56 improvement.
