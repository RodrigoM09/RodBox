# PB45: recover after late host rate selection and defer busy controls

PB44's hardware log confirms DMA-loaded packets remained unsent and bounded retries activated. During the second stream start, the final failed attempt occurred at 2226.869810; the matching host SET_CUR arrived at 2226.873331. The pump had stopped roughly 3.5 ms before that command. The rate setter updated the rate but never restarted the failed pump. PB44's filesystem check passed with no log allocation error.

PB45 lets a valid, matching host rate command restart an enabled non-native USB audio pump. An already-running pump remains untouched; an explicitly restarted stopped pump resets its audio endpoint and priming budget. Disabled streams, unsupported rates and stale mismatched rates do not trigger this recovery. IRQ failures still stop the pump; there is no timer-based endless retry or automatic advancement of PCM on each failure. This fixes a demonstrated recovery gap; it does not prove the controller will complete packets after recovery.

The two PlayCurrentSelection failures came from button_queue_try_post rejecting a nonempty queue, not a full or broken queue. Play/Pause now retains one pending transaction and retries posting through the normal control tick for up to five seconds. It posts once, waits for the requested state and returns failure on timeout. If the state changes independently, it does not send an unwanted toggle. Queue pressure is no longer logged as an assertion. Other outstanding transactions remain protected from overwrite.

Validation: all 26 USB test scripts passed. Production-code harnesses cover matching late rate commands, disabled/invalid/stale-rate exclusions, restart failure, actual busy-control dispatch, delayed posting, one-shot behavior, independent state changes and timeout. Existing batch tests cover 40,571 failed completions without further PCM consumption. Native ipod6g build, image checksum, artifact hashes and tracked-source identity passed.

Built only: not installed, no device or music writes. Lexus sound, normal playback timing, live metadata and clean filesystem require hardware acceptance. Source and tests retain the PB44 logging fixes.
