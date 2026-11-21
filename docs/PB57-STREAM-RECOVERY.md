# PB57: keep Lexus USB audio playing after the hold switch

Version: `rodbox-pb57-hold-stream-261120`. Base: PB56 (`checkpoint/pb56`, `9d832fa`).

**Status (2026-11-20):** installed and read-back verified on the test iPod. The first install attempt stopped at the read-only FAT preflight before writing anything (exit 206: one damaged album-art cache thumbnail and an off-by-one free-cluster count). With the user's approval, only that volume was repaired with `diskutil repairVolume`. The thumbnail is now empty; the firmware refuses it and **Update Art Cache** can rebuild it. Protected files, firmware and music sizes/dates were unchanged, and the check after the repair was clean. The guarded installer then replaced only the core and version file, read back all 42 firmware files, ran clean FAT checks before and after, and safely ejected. **In-car acceptance is pending.**

## Reported problem

Connected to the 2015 Lexus ES350 over the 30-pin-to-USB cable, sliding the iPod's Hold switch on and then off stopped the music. It came back only after unplugging and reconnecting the cable.

## What the code showed

No retained device log contains a car session in which the switch was moved. The only PB56 car session on the player streamed normally until the cable was removed. So the mechanism below is inferred from the code and earlier traces, not captured during the failure.

- The USB iAP audio stream sends one isochronous packet at a time. `batch_xfer_complete()` in `usb_core.c` runs in the USB interrupt. Since PB36, a failed or short completion stops the pump and deliberately does not retry in interrupt context.
- Before PB57, only an explicit host command restarted the stream: `SET_CUR` (sample rate) or `SET_INTERFACE` alternate 1. This happens at connection and at rate changes. A car that keeps the interface enabled and keeps polling never sends either command again, so a single missed packet left the stream silent until reconnection. That matches the symptom exactly: playback stalls and only a replug helps.
- Moving the Hold switch makes the player do several things at once: clickwheel power-down/re-initialization in the tick interrupt, an immediate backlight change (the default “backlight on button hold” setting is Off), LCD sleep/wake, storage pre-wake and a status-bar redraw. None of these touches the USB stream directly. However, any delay in servicing the USB interrupt past the next isochronous interval produces one missed packet. Earlier logs show `iso ... incomplete` / `iso ERROR` entries, which are the way such a miss appears. PB56 recorded established-stream recovery as deferred work.

The hold switch is the user-observed trigger. Which specific hold-time activity delays the packet has not been measured.

## Change

1. `usb_core.c`: `batch_fault` is set only when a failed/short packet or failed submission stops a running stream. Every explicit start, stop or initialization clears it. `usb_drv_batch_faulted()` reports it. The interrupt path still only stops the pump.
2. `iap/audio.c`: `iap_audio_recover_stream()` runs on the USB thread, the same thread that handles `SET_INTERFACE`/`SET_CUR`. If the host still has alternate 1 enabled and the pump is fault-stopped, it makes the same `usb_drv_batch_start()` call a host `SET_CUR` makes: reset the endpoint, prime it again and send new PCM. A packet is never sent twice.
   - Backoff: three immediate attempts, then one per second up to attempt 60, then one every 10 s. The count resets after 2 s of healthy streaming. A host that truly stopped reading costs about one millisecond of track per attempt, not a runaway drain.
   - `SET_INTERFACE` alternate 0, disconnect or an explicit stop ends recovery. A stop is never treated as a fault.
3. `usb_iap.c`: the 100 ms iAP tick calls the recovery before any early return, so a pending play/pause wait cannot delay it. It also logs each Hold switch change with play state, stream alternate, fault state and current sink.
4. `usb_log.h` / `usb_log_file.c` add log text:
   - `iap: stream stopped by a failed packet, restarted (attempt N)`
   - `hold switch on|off: playback …, stream alt …, sink …`

The controller driver, descriptors, PCM/mixer, sample-rate negotiation, notifications, codecs and the library are unchanged. All 40 codecs are byte-identical to PB56.

## Tests

`tests/usb/test_pb57_stream_recovery.py` compiles the production batch pump and the production recovery function together under ASan/UBSan. It drives them with a simulated host that keeps the interface enabled.

- **RED, against PB56 sources:** after one failed packet, the stream stays stopped for a simulated minute (0 packets, 0 restarts). The tick also has no recovery call before its early return.
- **GREEN, against PB57:** the next tick restarts the stream and audio flows again. After 2 s of health, the next fault counts as a first attempt. A host that never reads gets 65 bounded restarts in 120 s, using one packet of PCM per restart. Restart logs are rate-limited. Disable, explicit stop and an exhausted source are not treated as faults.

The full suite passed 82 of 82, including all 41 USB scripts, with existing batch-failure, ISO recovery, startup and Lexus fixtures unchanged. The native ipod6g/64 MB build passed with the same five pre-existing warnings, none in changed files. Firmware-source hashes did not change during the build.

## Limits

- Host tests do not reproduce the hold switch, interrupt latency or the Lexus. Physical acceptance is the user's in-car test.
- If the failure persists, PB57's log will show it. Look for `hold switch` lines followed either by `restarted` lines (recovery ran) or by nothing (a different mechanism, such as a paused player or an iAP control wait). Preserve logs before more browsing rotates them.
- Recovery restores the stream the car is already polling. It cannot recover a car that stopped polling or switched source; that case is ended by the car's own `SET_INTERFACE`/disconnect.

## First in-car result (2026-11-20)

The user reports that everything worked. The logs show two PB57 car sessions:

- **Session 1:** at 87 s the stream hit a mid-stream isochronous failure with no host rate/interface command after it, the exact case that silenced PB56 until a replug. PB57 re-primed the stream 86 ms later, and it played until unplug at about 48 minutes.
- **Session 2:** streamed steadily until unplug. Removing the cable caused one harmless restart attempt just before the disconnect.

After the sessions, all 42 firmware files matched PB57 and a read-only FAT check was clean.

The hold-switch log lines did not survive: database traffic rotated `usb.log` past the connection, and the audio log does not carry them. So the 87 s failure is consistent with a Hold toggle, but that is not proven. Next time, connect to the Mac soon after a Hold test.
