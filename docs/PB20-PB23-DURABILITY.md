# PB20–PB23 durability work

Historical scope: this page records PB20–PB23. [PB30 is the current experimental checkpoint](PB30-DIRECTORY-END.md). At PB23 publication, PB23 was the current experimental source checkpoint for ipod6g / S5L8702 / 64 MB. PB20–PB22 were installed and played music, but sustained verification still found changed song data. PB23 is installed with 42 core/info/codec files verified after remount and a clean filesystem check; its device acceptance is pending. No permanent corruption fix is claimed. Main remains the locked stable reference.

The following work preserves the PB1–PB19 PodBox/Scrim integration, Music/Audiobooks flow, native audiobook progress, analysis, settings and headset changes. Actual headset-control behavior remains unresolved despite host input tests. The unfinished station work is excluded.

AI assistance: three GPT-6 Astra reviewers examined USB/storage, library/artwork and playback foundations; Codex integrated the changes, added regression tests and built native candidates. Licensing and upstream attribution are unchanged.

## Confirmed defects corrected

### USB and storage

- Failed storage writes no longer replace an outstanding prefetched OUT transfer with a command receive. Remaining command data is drained without more disk writes; failure residue survives short/error drains.
- CBWs must have a successful, exact-size receive and valid header, command length and data phase. Truncated commands, direction/length mismatches, failed CSWs and stale opposite-direction completions cannot dispatch writes as if they were commands.
- Class reset cancels the supported storage endpoints, purges their queued completion events only, then receives a fresh command. Other classes and control events keep their order.
- 64-bit LBA multiplication/addition and transfer-size arithmetic are bounded before use. Negative, empty and out-of-disk ATA requests are handled before partial-sector memory copies.
- Capacity replies fully initialize and serialize their address fields. Zero or invalid sector geometry is rejected before division, shift or last-LBA subtraction.
- Failed READ and SMART requests no longer return stale transfer-buffer bytes as successful data.
- ATA flush propagates readiness, command, timeout and device errors. Idle sleep retains power after failure. USB synchronize-cache and safe eject perform and check the flush; failed eject retains host ownership. Repeated eject does not access storage already returned to playback.
- Packed ATA error codes now use defined unsigned bit operations; the storage suite no longer suppresses signed-shift sanitization. IDENTIFY sector arithmetic is validated before shifting/multiplication.

### Library, artwork and analysis

- A short library write latches failure so later finalization cannot publish it. Paths, record counts, record batch lengths, native file sizes and write sizes are checked.
- Append/marks operations report late flush/close failures and attempt to restore a torn header. Transient read failures are distinguished from confirmed invalid data.
- Analysis working-file reads, seeks, writes, truncation, periodic flushes and pause close errors are checked. Failed measurements stop the scan and cannot publish a partial replacement. Resume/header/allocation/offset bounds are enforced.
- Calibration refuses incomplete reads and saves by checked replacement. Unreadable-track lists preserve the previous file after failed publication.
- Artwork files check flush/close before rename. Failed thumbnail or stamp saves stop the pass instead of declaring the cache complete. Thumbnail dimensions, read offsets and scaling arithmetic are bounded.

### Playback, saved state and controls

- Audiobook progress rewrites reject incomplete record/path reads instead of replacing the file with its readable prefix.
- Save operations copy current metadata under its existing playback lock. Failed completion saves retry; successful saves acknowledge only the matching event generation. Newer completion events remain pending.
- Rapid accepted headset clicks keep their separate classification slots. The original six-poll delay, debounce, volume safeguards, pulse durations and default setting are retained.
- Failed startup promotion of settings/resume `.new` files restores the preceding active file when possible; failed backup creation stops promotion.
- Audiobooks placement correctly follows Music even when Music was the last menu row.

## Continued corruption investigation (revision 2)

The additional review follows the errors all the way from the ATA driver through filesystem metadata updates and application shutdown. Reproduced defects are plausible contributors, not a determination of which event damaged this card. The available history records PB19 changing eight ATA cache-invalidation lines; the other reviewed core filesystem paths were carried in the pinned foundation import. These findings therefore do not establish that every defect was introduced by the latest RodBox changes.

- Packed ATA errors could overflow during `rc * 10 - stage` and become nonnegative, while the filesystem uses negative returns to detect failure. Error context now remains bounded and negative. Tests inject real high-bit Classic error codes at all eight cached read/write stages; the prior candidate reproduces signed overflow and a false-success return.
- Increasing the physical-sector emulation multiplier could reuse a cache entry loaded at the preceding smaller size. A partial-sector write could then overwrite neighboring sectors with stale/unfilled cache bytes. The setter now serializes with ATA I/O, invalidates the cache before increasing its size and rejects non-power-of-two sizes. A byte-exact mock disk reproduces neighboring-sector rollback in the prior candidate and verifies the corrected path in single- and multi-drive configurations.
- Partition discovery now rejects a failed MBR read even if its partially filled buffer contains a plausible signature. GPT headers and entry sectors are parsed only after successful reads; invalid geometry and unsupported or malformed entry sizes are rejected before unsafe arithmetic or field access. The actual `disk_init` function is tested with injected partial failures and malformed entries under ASan/UBSan in both ordinary and virtual-sector configurations. The preceding candidate fails the new MBR-read regression.

- Filesystem mount now validates scaled sizes with wide arithmetic before storing native fields; rejects overlapping/empty FAT layouts, inadequate FAT capacity, unsupported FAT counts, invalid roots/FSInfo locations and volumes extending beyond the physical device. Valid FAT16/FAT32 layouts using 512–4096-byte logical/virtual sectors remain covered. A preceding mount's FAT16 flag and free-space hint cannot contaminate the next mount; invalid current hints trigger recalculation instead of driving allocation. Normalized FAT16 table size no longer truncates to 16 bits. The prior candidate fails the new malformed-layout regression.
- Accepted shutdown now quiesces the artwork/file-index worker, waits for active pass cleanup with safe battery power and prevents queued callbacks/ticks from restarting writes. USB acknowledgment remains serviceable. Critical-battery shutdown requests cancellation without an unbounded wait. Twelve actual-body tests cover the worker and a real host-mutex wait.

- FAT allocation reserves a new cluster before linking it and checks each update. Chain-read failures stop freeing/truncation rather than becoming cluster addresses; invalid/free/reserved links are bounded before cache access, and stream/seek operations propagate those failures. Empty-file close commits the detached directory reference before releasing its chain. Regression cases reproduce a live link to an unallocated cluster and a directory entry referencing freed space in the earlier source.
- Failed bounce-buffer reads no longer copy stale bytes into the caller. A failed forced writer close now stops with a diagnostic before USB unmount discards the caches. This is a visible error halt requiring restart, matching existing FAT metadata-write failure policy; it does not undo writes that already failed.
- The database worker also honors a persistent accepted-shutdown gate and waits for current work/cleanup. Queued rebuild/update/import/load/timeout work cannot restart after preparation returns. Busy-merge rejection remains cancellable, USB waits release the worker barrier, and the explicit final foreground flush remains available. Twelve actual-function regression cases pass; the earlier source reproduces writes after accepted shutdown.

- Serial accessory storage handoff now cancels artwork and waits for active library work before acknowledging USB. Worker dequeue/dispatch and job purge share a barrier, pending EXIT is preserved, shared claims/buffers remain intact, and late serial dispatch is gated during host ownership. Creation/close/reclaim ordering is serialized and serial packets claim their transport before library access. Actual-source tests cover cancellation, purge/dequeue interleavings, a real blocking barrier, reclaim, resume and full artwork buffers; the preceding core reproduces an early acknowledgment. Generic accessory poweroff quiescence remains unchanged and is not certified by this USB fix.

## PB21: serialized verified writes

For iPod Classic, finish storage write/readback before receiving the next USB buffer. Compare the written bytes and refuse success after read errors or mismatches, preserving failed-command draining and residue. This removes an overlap for hardware testing; it does not prove overlap caused the observed failures.

## PB22: ATA command settling

After command/device-select writes, drain the PIO controller and wait two microsecond timer ticks before status polling. This avoids accepting the previous ready status before the device updates BSY. Ordinary data-register words do not receive that delay. Actual helper/flush polling tests reproduce early completion in PB21 and pass with the delay. See the [ATA non-data protocol, section 9.4](https://www.seagate.com/support/disc/manuals/ata/d1153r17.pdf#page=272).

## PB23: write-through USB verification

Flush each verified write before readback and success; a volatile cache read alone cannot establish persistence. Flush errors use the same failed-write drain/sense/residue path. This iPod path is write-through even for FUA requests, which the preceding write arm ignored. Actual host FUA flags were not captured, so that omission is not claimed as the observed trigger. See [SCSI FUA write semantics](https://www.seagate.com/files/staticfiles/support/docs/manual/Interface%20manuals/100293068j.pdf).

## Validation and limits

PB20's 41-suite host run passed. PB21 passed 11 focused USB suites; PB22/PB23 passed 21 focused storage/USB suites. Each candidate built natively with Arm GNU 13.2.Rel1 and 40 matching codecs; model headers, checksums and versions were checked. PB23's full 43-suite publication run passed in a clean checkout and is recorded in its checkpoint. Tests use production bodies with mocked services and ASan/UBSan; they do not simulate electrical behavior or establish hardware safety. The new write-through test models volatile cache separately from persistent storage and injects flush, write and read failures.

Observed changed regions included exact block-sized spans even when the FAT check passed. The most recent changed payload matched none of the 111 recently transferred source files. No captured trace proves a single root cause; ATA/iFlash/card/cable/USB behavior remains unexcluded. A device that falsely reports flush completion can defeat the new check. FAT is not journaled; power interruption, failed in-place rollback and emergency shutdown remain risks. Generic accessory poweroff quiescence remains unchanged.

At PB23 publication, the full music restore was stopped. The next acceptance was the same failed approximately 2 GiB transfer, followed by remount hashes and playback/idle/reconnection checks. If it fails again, use the same batch through bootloader USB as a control rather than stacking speculative changes. Personal restoration scripts, media and device evidence remain local.
