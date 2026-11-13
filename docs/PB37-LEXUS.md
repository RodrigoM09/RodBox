# PB37: stop runaway audio consumption on failed USB transfers

Version: rodbox-pb37-audio-stop-261102
Status: Installed and tested: failure flood stopped, but Lexus audio remained stalled.

PB36 hardware test failed: 40,571 failed packets in 5.1 seconds, noise and
accelerated track time. The non-native batch pump pulled fresh PCM after
every error, using interrupt frequency instead of delivered audio as its clock.

PB37 changes:
- Only successful, full-length packet completions pull the next PCM packet.
- Any failed, short, negative-length or oversized completion stops the stream.
- Failed submissions stop it too. No IRQ-context automatic retry, no stale
  completion consumption after stop. Explicit interface restart can try again.
- Start is idempotent while running; stopped streams cannot pull more data.
- Incomplete-ISO error logs use the existing per-endpoint cap, preserving other
  diagnostics instead of flooding rotation.

This is a fail-stop fix for the PB36 regression, NOT a claim of working Lexus
digital audio. On the unresolved scheduling fault PB37 intentionally goes
silent rather than burning through the song or emitting repeated bursts.
PB36 metadata/artwork handlers are retained; their car acceptance is pending.

Verification:
Six focused ASan/UBSan suites passed: batch failure flood, ISO endpoint recovery
and log cap, metadata streaming, artwork dispatch, filtered database lookup,
and playback/rate handling. The production pump survived a 40,571-error
simulation with zero extra PCM pulls/submissions after the first failure.
Native ipod6g/64 MB build passed. Source matches build worktree; artifact
SHA-256 recorded. No attached-device or music-file writes performed.

PB36 remains installed until PB37 installation is explicitly requested.

## Publication status

Installed and tested: failure flood stopped, but Lexus audio remained stalled. Source reconstructed from the saved cumulative PB35-based patch and verified against build source hashes. Native builds are historical; host regression tests are rerun on final published source. Music inventories and filesystem checks are not full-library checksum verification.
