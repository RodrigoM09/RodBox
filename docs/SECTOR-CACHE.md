# PB19: keep partial-sector emulation coherent

Status: prepared, native-built and host-tested; **not installed**. The deployed
player remains on PB16 with device writes paused after recurring filesystem
damage. This is a confirmed code defect, not a confirmed diagnosis of that
player's corruption.

## The defect

Rockbox's shared ATA layer emulates partial access to larger physical or virtual
sectors. A small access loads a whole block into a read-modify-write cache. Full
block writes bypass that cache. Previously, they left its old contents marked
valid: a later small read could return stale bytes, and a small write could copy
those bytes back over neighboring sectors that had already been updated.

Separately, a failed partial write left modified cache bytes marked valid even
though the disk might contain none, some or all of that write. A subsequent read
or partial write could rely on data whose persistence was unknown.

PB19 invalidates this cache before full-block writes and after any failed write,
while holding the existing ATA mutex. It changes no sector geometry, transfer
mode, hardware timing, sleep policy, partition, bootloader or USB protocol.
The shared layer can affect other ATA targets; only ipod6g has been native-built
for this checkpoint. The original Rockbox copyright/licence is retained. This
focused fix and its tests were prepared with AI assistance; see [credits](../CREDITS.md).

## Evidence

`python3 tests/storage/test_sector_cache.py` compiles the actual production
cache/read/write region with a mocked byte-addressable disk, not a reimplementation
of those functions. Both single-drive and multidrive configurations pass with
AddressSanitizer and UndefinedBehaviorSanitizer:

- Small cached read, overlapping full write, then small read.
- Small cached read, full write, then small write; neighboring bytes must survive.
- Failed writes that change none, half or all of the requested physical block;
  subsequent reads must match the mock disk and later writes preserve neighbors.
- Multipliers 1, 2, 4 and 8 with 512-byte logical sectors, 40,000 differential
  mixed operations in total, plus native 4096-byte logical-sector access.

The original code fails each independently selected group: `--scenario read`,
`rollback`, `failure` and `mixed`. Removing either new invalidation separately
also fails its corresponding regression. The previous 220 ATA policy/reset
scenario/configuration checks and the native ipod6g build still pass.

## What this does not establish

The stale-neighbor path requires partial-sector emulation and an overlapping mix
of full and partial accesses. A host reporting 4096-byte blocks does not tell us
whether the underlying ATA device is native 4K or emulated, nor which accesses
actually occurred. Ordinary aligned filesystem traffic may not trigger it.
No captured device trace yet ties this defect to the observed damaged FAT chains.

The mock cannot establish cable integrity, adapter/card health, power-loss
durability or ATA flush-command behavior. Other confirmed USB error-recovery and
flush/error-propagation concerns remain separate. Do not repair repeatedly or
install this onto a failing filesystem merely because host tests pass. Retain
independent recovery backups and establish a stable installation path first.
PB17/PB18 are separate prepared changes; a cumulative PB19 image also includes
them and must not be presented as an isolated device test of this cache fix.
