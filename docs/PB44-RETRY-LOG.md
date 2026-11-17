# PB44: packet-based retry eligibility and durable USB logs

PB43's Lexus test recorded two first-packet errors, zero successful completions and no re-prime events. Firmware hashes passed. Read-only filesystem verification found usb.log with 96,805 logical bytes but 196,608 allocated bytes; it reported no cross-links or orphaned clusters.

## Audio

PB43 required the DMA transfer-size register to equal the original request length. The driver's existing FIFO accounting distinguishes bytes pushed into the FIFO from packets pulled onto USB: a DMA-loaded, unsent packet fails that comparison. PB44 captures the size register before flushing and permits the bounded startup retry only for a single packet that remains unsent. Multi-packet requests, already-transmitted packets, established streams and exhausted retries remain excluded. The buffer is unchanged and no failed attempt consumes additional PCM. Diagnostics now record the raw register and requested size so hardware can confirm eligibility. The prior trace did not contain this register, so the hardware explanation remains a testable inference.

## Logging

The USB writer previously advanced its ring cursor without checking formatted writes or explicitly confirming persistence. It now checks complete line writes and synchronizes both logs before advancing the cursor under the existing lock. Failure retains the ring entries (retry can duplicate lines). USB diagnostic files alone are trimmed to their current logical EOF between synchronization calls, reconciling excess allocated tail clusters without touching music or general filesystem code. Tests cover failed sync, failed trim and short writes. This hardens the observed failure path; it does not prove why the original excess allocation arose or provide atomicity under power loss.

## Validation and scope

All 25 USB test scripts passed, including sanitizer-backed production-code harnesses. Native ipod6g/64MB build passed. Firmware header/checksum, artifact hashes and tracked build-source identity verified. Tests model register/file API behavior, not full controller/FAT hardware.

Built only: no device writes, repairs, installation or music changes. PB43's existing filesystem issue remains on the device. Lexus audio, retry activation and filesystem cleanliness require a later hardware test; live metadata acceptance remains unverified.
