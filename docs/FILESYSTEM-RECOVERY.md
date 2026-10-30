# Filesystem recovery and remaining acceptance

## Historical PB16–PB18 recovery record

The following describes that earlier checkpoint, not the currently installed build. See the PB28 and PB30 follow-ups below for later results.

Persistent font read errors and failed filesystem checks followed the write
failures. Normal restart and another host port did not clear those read errors.
The independent firmware/settings/progress backup was reverified before repair.

macOS volume repair found invalid, cross-linked and out-of-range FAT chains.
It made the filesystem consistent but shortened damaged files; repair alone did
not restore their contents. The damaged firmware folder was saved independently
and retained on the device. The exact known-good native PB16 folder was restored,
with full hashes after staging and final remounts. No formatting, partition-map,
bootloader or settings-feature changes were performed.

A full read of current music/art against the original active-library manifest and
explicitly approved additions identified sixteen damaged tracks, two damaged
covers and one missing artist image. Some bad files retained the expected size.
Damaged versions were preserved before exact replacement. All nineteen recovery
files passed hashes after remounting and a read-only filesystem check. Deleted
archive-only songs were excluded. Native firmware files and audiobook contents
were checked again, with a complete independent after-recovery backup.

PB16 remains deployed. PB17 and PB18 are prepared only. The user confirmed normal
theme appearance, playback/seek and audiobook resume after a clean shutdown and
restart. However, the next read-only filesystem check found new invalid music
cluster chains, directory-end inconsistencies and a damaged resume temporary
file. The PB17 installer stopped at its prerequisite check before staging or
publishing anything. No new bulk transfer occurred between the clean recovery
check and this failure. Functional playback alone is therefore insufficient
acceptance, and large transfers alone do not explain all observed corruption.

At that checkpoint, further device updates and transfers were paused. Sustained-transfer reliability
and the original corruption cause remain unresolved. Host filesystem/file checks
cannot establish power-loss durability, card health or accessory behavior.

The USB error-recovery host reproducer is deliberately separate from acceptance
checks. Run `python3 tests/usb/reproduce_write_error.py` from the repository root;
at this historical checkpoint it exited 1 for the outstanding-OUT overlap. It uses actual
extracted MSC code with mocked endpoints/storage and no physical USB access.
It does not prove that overlap caused the initial write failure. Correct
protocol recovery needs a separate tested fix. See [audit status](AUDIT-STATUS.md).

## Follow-up through PB28 (2026-10-30)

The full library restore and post-repair checksum pass later completed under PB27. Further artwork activity preceded 13 orphan clusters. PB28 corrects a demonstrated deferred-unlink leak at unmount; the old clusters were separately repaired without formatting. The first PB28 restart/reconnect is clean. These later observations do not retroactively resolve older direct-reader inconsistencies or establish a single historical corruption cause. See [PB28 evidence](PB28-ARTWORK-CLEANUP.md); private device-specific recovery scripts remain excluded.

## PB30 diagnostic-report recovery (2026-10-30)

PB29 later exposed duplicate `unreadable.txt` / `unreadable.dat` directory records and cross-links, including a shared reference with the playlist-control file. A prior successful filesystem repair alone had left duplicate names, so the next check failed again. PB30 fixes the reproduced directory end-marker defect; it does not automatically remove already-exposed records.

The approved recovery backed up protected files, repaired cross-links, verified the filesystem, and only then removed all duplicate disposable diagnostic reports. Clean remount checks separated removal passes. PB30 installation preserved protected data and music inventory/size/timestamps without formatting or music edits. After normal playback/artwork, shutdown and restart, the first PB30 reconnect was clean; each diagnostic report regenerated once. Full audio checksums were not repeated. See [PB30 validation](PB30-DIRECTORY-END.md).
