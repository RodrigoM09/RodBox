# PB43: bounded first-packet recovery

PB42's Lexus retest started three ISO packets, each ending in an immediate zero-byte error. There were no successful completions. PB43 addresses the one-attempt startup failure; hardware acceptance remains pending.

On S5L8702, an incomplete first packet can be re-armed only after endpoint-disable acknowledgement, with unchanged transfer size and the same request buffer. The next attempt uses the opposite microframe parity. Eight re-arms are allowed per stream reset; exhaustion, partial progress, and errors after the first completion retain fail-stop behavior. No failed attempt reports success or pulls new PCM. Re-arming clears the disable command. Successful completion anchors subsequent scheduling to the observed bus frame. Bounded retry diagnostics identify frame and attempt number.

The generic token-synchronized startup remains unchanged. EP0 and bulk-storage endpoints are excluded. This change does not modify music or storage handling.

Validation: all 24 USB test scripts pass; register-mocked production code covers deferred disable, retry bounds, buffer ownership, partial-transfer rejection, established-stream rejection, parity selection, stale completion handling, and 14-bit frame wrap. Address/undefined-behavior sanitizers cover the C harnesses. Native ipod6g build and image header checksum verified. These tests do not emulate the complete controller or establish Lexus audio compatibility.

Next hardware acceptance: sustained successful packet completions, advancing playback at normal speed, audible clean audio, and clean filesystem after reconnect. Installed after separate approval: all 42 firmware files and 1,370 protected files verified; database and artwork checks passed; filesystem clean. The inventory, sizes and modification times of 2,243 music-folder files were unchanged. No music writes or full-library checksum repeated. Persistent USB logging retained and the iPod safely ejected.
