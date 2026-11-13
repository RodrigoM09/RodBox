# PB40: audio restart and sample-rate transaction cleanup

PB39 logs showed an ISO request waiting without completion, then a subsequent stream enable failing. A logical batch stop left its controller request busy. Stop now disables callbacks before resetting only the audio endpoint, releasing its pending request before restart. Non-native enable always consults the idempotent pump start so a failure-stopped pump can restart despite the previous enabled flag.

Rate announcements now serialize while awaiting acknowledgement, coalesce queued changes, and record the actual transaction ID only after successful submission. Stale/late acknowledgements cannot resolve a different announcement. Rejected attempts remain due for retry. One timeout completes both protocol and PCM pending state; its deadline follows the transaction ID. The existing permissive timeout fallback remains, rather than adding a new policy.

Validation: native ipod6g64MB build passed without compiler warnings. Ten focused suites pass, including 50 hardware-busy stop/restart cycles, failure-flood PCM protection, queued-rate coalescing, failed submission, stale/late ACKs, and transaction timeout renewal. Host tests do not prove working Lexus audio or resolve why the initial host-token event was absent.

Prepared as rodbox-pb40-restart-261103. Installed and verified; Lexus hardware acceptance still pending. No iPod, settings, filesystem, or music-file writes were performed for this code-fix task.

## Publication status

Installed and verified; Lexus hardware acceptance still pending. Source reconstructed from the saved cumulative PB35-based patch and verified against build source hashes. Native builds are historical; host regression tests are rerun on final published source. Music inventories and filesystem checks are not full-library checksum verification.
