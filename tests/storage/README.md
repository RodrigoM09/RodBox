# Classic ATA USB idle regression checks

Run `python3 tests/storage/test_usb_idle.py` from the repository root. The runner
copies the current production function bodies without rewriting their logic into
a C harness and compiles them with Clang AddressSanitizer and UndefinedBehaviorSanitizer.

The 33 scenarios cover:

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
That gives 132 executed scenario/configuration combinations. Tick wrapping uses
the same `-fno-strict-overflow` option as the firmware's build configuration;
the host's `long` width need not equal the iPod's 32-bit `long` width.

Two inherited target conventions need explicit host-harness accommodations:

- `mmcdefs-target.h` error macros are copied verbatim. They encode errors by
  shifting a signed high bit, so only UBSan's `shift-base` check is disabled.
  Other undefined-behavior checks remain enabled.
- The actual write wrapper casts its buffer through the target's 32-bit address
  width. Host pointer-cast warnings are suppressed; the write failure test must
  return before dereferencing, DMA setup or data transfer.

The harness checks the public read/write wrappers' mutex release. It does not
exercise existing soft/hard reset error paths or their separate lock semantics.
