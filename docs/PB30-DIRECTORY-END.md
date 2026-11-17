# PB30: preserve the FAT directory end marker

PB30 (`rodbox-pb30-dirend-261030`) fixes `add_dir_entry()` in `firmware/common/fat.c`. All preceding firmware improvements, including PB28 reader cleanup and PB29 Menu navigation, are retained. The bootloader is unchanged.

## Defect and correction

FAT uses a directory entry whose first byte is `0x00` to mark the end of the live directory. Bytes after that marker need not be zero; they can contain old file records. The previous insertion path treated that space as free but did not move the marker after consuming it. Adding a new filename could expose stale records referring to storage that had already been freed or reused, producing duplicate names and cross-links. Stale occupied bytes inside a new long filename's slots could also trigger the free-entry assertion.

PB30 remembers the first end marker, clears the consumed stale slots, and establishes the successor marker before publishing the new filename. Filling a deleted gap before the marker preserves its live neighbor. A full directory chain does not allocate another cluster solely for a terminator, and a failed successor read prevents filename publication. This is not a journal or a guarantee of atomic recovery from power loss.

The connected PB29 filesystem had three `unreadable.txt` entries and two `unreadable.dat` entries. Two text entries shared storage; one binary-report entry shared storage with the playlist-control file. This matches the reproduced mechanism, but there is no raw historical trace proving the cause of every earlier corruption event.

## Verification

- The same regression fails the old PB29 production functions and passes PB30 under AddressSanitizer/UndefinedBehaviorSanitizer. It covers stale successors/consumed slots, live neighbors, 512/1024/2048/4096-byte sectors, directory boundaries and successor-read failure.
- Eight focused host suites passed; see [TESTING.md](TESTING.md). The preceding 47-suite run belongs to PB28 and was not repeated for PB30.
- The native ipod6g / S5L8702 / 64 MB build passed with Arm GNU Toolchain 13.2.Rel1. All 40 codecs match PB29 byte-for-byte.
- Approved recovery repaired the existing cross-links and then removed every duplicate disposable diagnostic report, with clean checks between removal passes. Installing the code alone would not remove existing duplicate records.
- Installation verification passed: 42 firmware files, 56 artist images, 594 cached-image structures and 732 backed-up protected files checked, allowing only the intended core/info replacement. Music inventory, sizes and timestamps were unchanged; no full music checksum pass was repeated. No formatting, music edits or bootloader changes occurred.
- The user then confirmed normal PB30 startup, playback, artwork, shutdown and restart. The subsequent read-only filesystem check passed with no cross-links or orphaned clusters; cache-name enumeration found no duplicates, and both diagnostic reports regenerated as single files. That reconnect check did not repeat artwork hashes or full music checksums.

| Local build evidence | Value |
| --- | --- |
| Core bytes | 1,995,724 |
| Core SHA-256 | `39f8cab06bfd401590837db40929c1da172a8f80626bbc6cd8c6deec1a637646` |
| Source checkpoint | `checkpoint/pb30` |

The regression uses the production directory insertion/name-writing functions with a byte-array directory/cache and mocked storage. It is not a complete FAT image or hardware emulator. One clean physical cycle does not certify sustained USB transfers, all power-loss cases or all historical corruption causes. Private binaries, reports, music, images and device-specific repair scripts are not published. See [recovery notes](FILESYSTEM-RECOVERY.md).
