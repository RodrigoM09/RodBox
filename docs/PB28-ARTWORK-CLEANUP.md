# PB28: deferred artwork-file cleanup at unmount

PB28 (`rodbox-pb28-artcleanup-261030`) retains PB27's database correction and the earlier storage, playback and artwork features. It changes the native filesystem close path, not image selection or music metadata.

## Confirmed defect

The artwork cache writes a temporary `.new` file, checks its writes/flush/close, and renames it over the old `.aat` image. An existing reader can keep the old image open. Normal close defers freeing that removed file's cluster chain until the last reference closes.

The volume-unmount callback previously discarded read-only stream bindings directly. If such a reader was the last reference to a replaced/deleted file, that bypassed `close_stream_internal()` and its `FAT_RM_DATA` cleanup. The allocated chain then had neither a directory entry nor a surviving reader to free it.

PB28 adds `force_close_reader_internal()` and routes unmount readers through normal close while the volume is still mounted. A failed deferred cleanup stops before USB handover, matching the existing fail-stop writer policy. Live files are not freed. The changed implementation is in `firmware/common/file_internal.c`, with declarations/routing in `firmware/include/file_internal.h` and `dircache_redirect.h`. The source version label is updated separately.

## Verification

- The old production callback fails the host test's allocated-cluster assertion; the corrected callback passes.
- The test extracts the actual callback/close functions and mocks FAT storage and stream bookkeeping. It covers one to four references, mixed reader/writer ordering, exactly-once cleanup, live-file preservation, and cleanup failure before handover.
- All 47 cumulative host suites passed; the focused test also passed from the publication checkout.
- Native ipod6g / S5L8702 / 64 MB build passed with Arm GNU Toolchain 13.2.Rel1. All 40 codecs match PB27 byte-for-byte.
- During separately authorized private recovery, 13 existing orphan clusters were reclaimed without formatting. Firmware, database/settings and artwork backups were verified. No music files were edited.
- The user confirmed normal PB28 startup and artwork. The first reconnect verified 42 firmware files, hashes of 56 added artist images, valid structure/size of 594 cached images, and a clean read-only filesystem check with no orphan clusters.

| Local build evidence | Value |
| --- | --- |
| Core bytes | 1,995,552 |
| Core SHA-256 | `e41402a5e8a6faeaf0dd49226db289d3b440417d7bda24b29cf9b39e3a60e562` |
| Source checkpoint | `checkpoint/pb28` |

The binary and private installation/repair scripts are not distributed. The hash identifies the tested private build; a rebuild with different dates/paths/toolchain inputs need not reproduce that hash.

## Evidence limits

This is a demonstrated leak path, not raw-sector proof of the origin of all 13 observed orphan clusters or every historical music-data mismatch. One successful reconnect is initial acceptance, not sustained USB/cache/power-loss certification. The full music checksum check passed before the later artwork work; the artwork update and PB28 installation checked music inventory/size/timestamps, not another complete audio checksum pass. Installing firmware does not repair orphan clusters already present.

## Related library follow-up

The selected full library transfer completed under PB27. A subsequent full post-repair comparison of 1,708 music/artwork files plus firmware/metadata checks passed, with a clean filesystem. Later artwork caching again preceded filesystem errors, which motivated the focused investigation above.

Distinct track-artist strings containing featured artists are not necessarily duplicate database records. An opt-in Artist menu using `albumartist` keeps an album under its Album Artist without rewriting music tags; see [the generic menu example](../examples/album-artist-menu.txt). Missing artist portraits can be supplied as separate album-local `.artist/folder.jpg` images. Existing lookup code already supports that layout; it is not a new PB28 feature. Personal photos, downloaded artwork, configurations, inventories and raw logs remain private.

See [TESTING.md](TESTING.md) for the regression command and device sequence, and [RECOVERY.md](RECOVERY.md) for backup boundaries.
