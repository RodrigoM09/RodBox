# Classic ATA USB idle regression checks

For the separate shared ATA partial-sector coherence checks, run
`python3 tests/storage/test_sector_cache.py`. This compiles the real production
cache/read/write region against a byte-exact mock disk in single/multidrive
configurations, with ASan/UBSan. `--scenario read`, `rollback`, `failure` or
`mixed` selects an independent group; `--source /path/to/ata-common.c` permits
comparison with an older source without editing the production tree. See
[PB19 and its limits](../../docs/SECTOR-CACHE.md).

Run `python3 tests/storage/test_usb_idle.py` from the repository root. The runner
copies the current production function bodies without rewriting their logic into
a C harness and compiles them with Clang AddressSanitizer and UndefinedBehaviorSanitizer.

The 57 scenarios cover:

- USB ownership before the timer decision, after the timer decision, and at the
  mutex boundary; no automatic controller clock gating or flash power removal.
- A completed real transfer refreshing activity while a stale sleep request waits
  for the mutex; the request must be cancelled after acquiring it.
- Deep-sleep checks re-evaluating USB ownership, backlight state and the deadline
  after acquiring the mutex.
- Fresh normal idle and deep-sleep grace periods after USB disconnect.
- Signed tick wrap across the host's `long` boundary for normal idle, deep sleep
  and the disconnect grace, using the actual firmware time comparison macros.
- Normal flash, rotating-disk and CE-ATA sleep; explicit shutdown sleep remains
  available independently of the automatic idle policy.
- Successful reads, chunk splitting, bounds errors, transfer errors, failed
  power-up before either read or write DMA/data activity, and balanced locks.

The same extracted bodies compile and run with `BOOTLOADER` and `HAVE_ATA_DMA`
defined independently and together. This is not a substitute for the full native
firmware build: hardware headers, interrupts and the real scheduler are mocked.
Lock hooks deterministically exercise selected interleavings; they do not prove
every possible concurrency ordering, physical USB reliability or flash health.
That gives 228 executed scenario/configuration combinations. Tick wrapping uses
the same `-fno-strict-overflow` option as the firmware's build configuration;
the host's `long` width need not equal the iPod's 32-bit `long` width.

PB20 packs ATA error values with unsigned 32-bit shifts before converting to
its signed API result. Full AddressSanitizer/UndefinedBehaviorSanitizer checks
now run without the former shift-base exclusion. `test_error_geometry.py`
checks 100,000 packed-code comparisons and IDENTIFY geometry bounds.

The actual write wrapper still casts its buffer through the target's 32-bit
address width. Host pointer-cast warnings are suppressed; the write failure
test returns before dereferencing or starting DMA/data transfer.

The harness checks public read/write wrappers and soft, hard and internal reset
mutex release. Reset cases inject failed power-up, readiness and CE-ATA reset,
including hard-reset fallback and recovery, both standalone and beneath an
already-held recursive caller lock. Packed error return values are checked.
The original 33 USB/transfer scenarios remain included.

## Continued PB20 corruption review

`test_sector_cache.py` also injects packed high-bit ATA errors at all eight
cached read/write stages and checks cache invalidation when the physical-sector
multiplier grows. Its `packed_errors` and `resize_cache` scenarios reproduce the
preceding candidate's false success and neighboring-sector rollback.

Additional actual-source ASan/UBSan suites:

- `test_partition_reads.py`: failed/partial partition reads, unsupported GPT
  entry sizes, ATA geometry and native 512–4096-byte sectors.
- `test_mount_geometry.py`: valid FAT16/FAT32 logical/virtual layouts, normalized
  FAT16 counts above 65535, malformed layout/capacity rejection and stale hints.
- `test_fat_failure_paths.py`: allocation, chain free/truncate, empty-file
  publication ordering, cluster bounds and failed stream/seek operations.
- `test_fat_bounce.py`: unsuccessful reads cannot copy stale bounce-buffer data.
- `test_unmount_writer.py`: failed final writer close stops before USB handover.

Filesystem and transport mocks reproduce specific failures. They do not make FAT
journaled or establish which event caused physical-device corruption.
