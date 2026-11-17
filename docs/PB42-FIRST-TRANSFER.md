# PB42: arm the first Classic USB audio packet

PB40 hardware evidence: stop/restart is acknowledged and rate negotiation progresses, but endpoint 81 stays disabled waiting for a first-token interrupt; no token or packet completion is recorded. The observed controller identifies itself as DWC 2.60a.

On the S5L8702 target, prime the first DMA packet directly for the next microframe rather than relying on that absent disabled-endpoint interrupt. Retain the original buffer, one-packet transfer size, frame parity and wrap handling. Other targets retain the token-based path. Failed/short transfers still stop the pump; no automatic IRQ retry or extra PCM consumption is added. Audio diagnostics identify direct priming separately from successful completion.

Validation: eleven focused suites passed. The production first-transfer test fails against PB40 and passes against PB42 across all 16384 frame positions and the generic-target path. Native ipod6g/64MB build and 40 codecs succeeded with Arm GNU 13.2.Rel1. Target header/checksum, build-source identity and artifact SHA256 checks passed. Fresh build reports existing unused Mikey helpers, undefined PNX0101 in plugin linker preprocessing, and the toolchain GNU-stack warning; changed USB files produced no compiler warnings.

PB41 host-helper/test changes are retained. Existing unrelated untracked duplicate-looking source files were excluded by building only tracked source plus the reviewed changes. Installed and verified: 42 firmware files, 1,370 protected-file checks, database/artwork and clean filesystem. USB logging startup override retained. Music inventory/size/mtime unchanged; no music writes or full-library checksum repeated. Safely ejected for the Lexus acceptance test. This removes the observed startup wait, but real Lexus audio/timing and live metadata remain unverified until an in-car test.

Reference: DWC2 first-token synchronization uses disabled-endpoint interrupts; the Classic trace does not show them in this DMA setup. https://code.googlesource.com/linux/torvalds/linux/+/e387dc122fc7c70c2a5df2567f4e2d1114f5a5da/drivers/usb/dwc2/gadget.c
