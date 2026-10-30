# PB27: database merge alignment and duplicate names

Historical checkpoint record, updated with follow-up on 2026-10-30: **PB27**, `rodbox-pb27-dbunique-261029`, for ipod6g / S5L8702 / 64 MB. It retains PB26’s reclaimable-memory bootstrap correction, the [PB24–PB26 improvements](PB24-PB26-STATUS.md), and earlier PodBox/Scrim and durability work. The bootloader, partition layout, themes and media are not changed by this firmware patch. `main` remains the locked stable reference; experimental work is on `community`.

## Problem and correction

PB26 could keep a non-word-aligned merge-buffer length after reclaiming playback-owned memory. `tempbuf_insert()` stores its descending CRC table as unsigned words at the end of that buffer. The production allocator/insertion regression reproduces a misaligned unsigned store under UBSan, a concrete defect in the duplicate-name checking path.

PB27 rounds the requested minimum up to `sizeof(uint32_t)` alignment after checking rounding overflow, and rounds the ordinary free-pool allocation down to the same alignment. The reclaim request still preserves playback headroom, and the returned merge buffer remains immovable. Only `apps-ipod/database/tagcache.c` changes in production code.

The regression extracts the actual allocator and insertion functions, with mocked allocation and CRC services. For both ordinary and reclaimed memory and all four length residues, repeated and case-variant synthetic artist names share one record; a different name stays separate. PB26 fails with the invalid access; PB27 passes. This is host evidence, not an emulation of the player’s CPU, USB, flash or complete scheduler.

## Build and installation evidence

The native Arm GNU Toolchain 13.2.Rel1 build and all **46 host suites** passed. The focused uniqueness regression was rerun for publication. Run `python3 run_audit_tests.py` for the cumulative suite and see [BUILD.md](BUILD.md) for target/core/codec instructions.

| Artifact | Recorded result |
| --- | --- |
| Core version | `rodbox-pb27-dbunique-261029` |
| Core bytes | 1995476 |
| Core SHA-256 | `6d51e1c41cefddbc4b2b61921dd9a75e48fddee5a66ff8679e16d38b29f47282` |
| Deployment checks | All 42 core/info/codec files matched after remount; filesystem check passed |
| Codec scope | 40 matching codecs verified unchanged from PB26; only core and build info needed replacement |

Firmware binaries and private installation/repair tools are not distributed in this source checkpoint. Build independently and keep matching assets/codecs; a successful build does not establish storage reliability.

## Existing database repair and on-device observations

The installed database already contained repeated identical names. A firmware allocation correction alone cannot remove rows already written. During separately approved private recovery, exact duplicate records in unique tag files were consolidated and master references remapped. Every track’s names, filename, numeric metadata and flags were compared before/after; play counts, ratings and resume values were preserved. Original database and firmware rollback copies were retained. No music file was rewritten or storage formatted by this installation/repair.

The user confirmed normal PB27 startup and one entry per artist. Post-startup checks matched all 42 firmware files, validated the database’s structure/references and unique names, obtained three identical full database reads, and passed the read-only filesystem check. This validates the repaired database and observed startup presentation. It does not prove that all future incremental commits remain duplicate-free; subsequent full-library checks are recorded below.

The verified music restore has resumed under PB27. All 475 previously copied music/artwork files matched before new copying; three additional approximately 1 GiB batches passed remount hashes and filesystem checks at the recorded publication checkpoint. At that publication snapshot the restore and final full-library acceptance were incomplete; see the completed follow-up below. Personal inventories, filenames, identifiers, databases, playback history and raw logs remain local.

## Remaining limits

No single cause of the earlier music-data corruption has been established, and PB27 is not advertised as its permanent fix. The batch restore and post-repair full checksum checks subsequently completed; repeated cache, playback, idle/restart and reconnection acceptance remains open. Physical headset controls, long-term battery behavior and comprehensive accessory validation remain unresolved. Host mocks and a repaired artist menu do not certify storage, DMA, electrical or power-loss reliability.

Codex assisted focused review, implementation, regression testing, build preparation and documentation. Upstream ownership and licensing remain unchanged; see [CREDITS.md](../CREDITS.md).

## Later full-library follow-up

The selected full restore completed, and the database reached 1,202 tracks with valid references and unique-name records. The full post-repair comparison of 1,708 music/artwork files, firmware and metadata passed with a clean filesystem. Album Artist grouping and separate artist-image sidecars were applied privately without rewriting music files. Later artwork caching preceded new orphan clusters; [PB28](PB28-ARTWORK-CLEANUP.md) addresses a confirmed unmount cleanup leak, without claiming every historical corruption cause is solved.
