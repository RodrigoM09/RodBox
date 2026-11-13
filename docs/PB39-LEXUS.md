# PB39: ISO service-window checks and track notifications

PB38 hardware retest remained silent with stationary playback time. Firmware hashes and read-only filesystem check passed. Database traffic rotated out initial audio negotiation evidence, so the exact hardware stall was not established.

Changes:
- Do not cancel an ISO request on a global incomplete interrupt before its target service interval. Use wrap-safe 14-bit frame comparison.
- Accept either NAK or IN-token/FIFO-empty for first-token synchronization, clearing stale token status before waiting. Retain same-buffer ownership and PB37 fail-stop protections.
- Send track-index notifications regardless of artwork readiness, avoiding dependence on image loading or PCM progress.
- Preserve bounded wait/token/completion diagnostics, stream status and errors in independently rotated usb-audio.log, through the existing storage-safe logging writer. Include firmware/session headers.

Validation: native ipod6g64MB build passed; nine focused suites passed (ISO interval/recovery, both token interrupt dispatches with stale completion, track notifications, batch failure, metadata wire format, filtered tags, endpoint ownership, artwork times, playback rates). These host tests do not establish working Lexus audio. In-car playback and live metadata updates remain acceptance tests.

No music-file editing or formatting. Reference for first-token events: https://code.googlesource.com/linux/torvalds/linux/+/e387dc122fc7c70c2a5df2567f4e2d1114f5a5da/drivers/usb/dwc2/gadget.c

## Publication status

Installed and tested: audio startup and restart failures preserved in diagnostics; filesystem clean. Source reconstructed from the saved cumulative PB35-based patch and verified against build source hashes. Native builds are historical; host regression tests are rerun on final published source. Music inventories and filesystem checks are not full-library checksum verification.
