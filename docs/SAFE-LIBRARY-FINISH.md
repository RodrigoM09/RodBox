# PB18: retain the previous library file after final write errors

Status: prepared and native-built; not installed. PB17 needs its separate runtime check first.

The generic library container and the finished sound-analysis index publish a
replacement by renaming a completed `.new` file. Their finalizers previously
ignored flush/close errors (the generic writer did not explicitly flush). A
late write failure could therefore still replace the previous good file.

PB18 requires successful flush and close before either rename. Close is attempted
exactly once even when flushing fails. A failed replacement is removed; the old
finished file remains, and sound-analysis working progress remains available for
retry. Existing file formats, records, calibration, DSP and playback are unchanged.
This detects errors surfaced by the filesystem API; it cannot promise SD-card
power-loss durability or compensate for lower storage layers hiding failures.

Tests compile the actual production finalizers. Eight generic-writer cases cover
success, caller cancellation, invalid descriptor, seek, short write, flush, close
and rename errors against real temporary files. The full sound-index harness
covers existing upgrade/resume/cache behavior plus injected flush and close
failures that retain the previous finished index. ASan/UBSan checks pass, and
restoring each original finalizer makes its added regression fail. The native
ipod6g build passes. Device analysis/cancel/resume acceptance remains pending.

The surrounding library/index implementation is inherited from PodBox on Rockbox;
this focused error-propagation change and fault-injection tests were prepared with
AI assistance. See [credits](../CREDITS.md). No evidence establishes that these
application-level errors caused the USB transfer failure.
