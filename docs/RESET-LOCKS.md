# PB17: release storage locks after reset failure

Status: prepared and host-tested; not installed. Bulk storage reliability remains unresolved.

Three Classic ATA reset paths returned directly on power-up failure while holding
the recursive ATA mutex. That could retain a lock level and block later storage
access. The fix uses the existing unlock-and-propagate macro at those three
returns. Packed error values, hardware timing and normal reset behavior stay the
same. It changes no USB pipelining, flush policy, partition or bootloader.

The actual reset function bodies now run in the storage regression harness,
including standalone and recursively locked callers, power-up/readiness/CE-ATA
failures and hard-reset fallback/recovery. All 55 cases across four configurations
pass (220 executions), including the preceding 33 USB/transfer cases. The native
ipod6g build passes. Mocked hardware and selected scheduling cases cannot establish
physical card or USB reliability. The original failing returns fail the added
regression checks. See [storage tests](../tests/storage/README.md).

PB16 booted normally and passed normal small-file USB writes and remount checks.
All previously checkpointed additions passed fresh full checksums. The following
write still failed with an I/O error and the subsequent read-only filesystem check
could not complete; the player was safely ejected. PB16 does not resolve that
failure. Neither this reset fix nor the remaining audit findings establish its
cause. Preserve verified backups; do not keep retrying bulk writes blindly.

These functions and the existing error macros come from Rockbox through the
credited PodBox/RockPod code chain. This focused cleanup and actual-function
regression coverage were prepared with AI assistance. Review is ongoing; a full
firmware audit has not been completed. See [credits](../CREDITS.md).
