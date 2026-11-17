# PB36: Lexus audio recovery and metadata candidate

Version: rodbox-pb36-lexus-261102. Native ipod6g/64 MB build passed.
Installed and tested: noise and accelerated playback time; superseded by PB37. No music, database, artwork or device files
were modified by this build task. No bootloader or partition changes.

## Changes

- Handle DesignWare incomplete isochronous IN interrupts. Disable only active
  busy ISO IN endpoints without an already-pending successful completion;
  wait for endpoint-disabled interrupt, flush that endpoint's FIFO, and
  report failure through the existing audio batch completion path so fresh
  data is queued. EP0, bulk/storage, inactive and masked endpoints are excluded.
  Ignore duplicate disabled events and clear state on flush/reset.
- High-speed audio retains its working parity, tries the opposite after an
  incomplete transfer, and writes one scheduling command rather than ORing
  opposing odd/even commands together. Full-speed next-frame behavior remains.
  This recovery addresses the observed stall path but real bus timing remains
  a hardware acceptance requirement.
- Implement GetDBTrackInfo and GetPBTrackInfo replies for capabilities,
  title, artist, album, genre, composer, duration, UID and album track number.
  Support the observed 0x20bf mask, byte-ordered masks, count/range bounds and
  one reply per field, advanced through USB send completion. Unknown fields
  fail explicitly; complete Extended Interface 1.13 support is not advertised.
- Resolve metadata through the current filtered database listing, not a global
  slot or unrelated playback index. Queue metadata uses the queue.
- Implement Extended Interface GetTrackArtworkTimes via the shared handler,
  validating format, track, artwork index, count and presence before replying.
- Fix unaligned numeric writes in libiap spans (reply values start at byte 5).
  Use the existing unaligned typedefs, matching the reader.

## Validation and limits

Four new ASan/UBSan suites passed: production metadata handler/streaming and
exact byte fixtures, filtered database accessor, artwork-time dispatch/bounds,
and ISO recovery selection/deferred completion. Existing endpoint invariants,
PB35 playback/rate and PB34 frame tests passed. Native build passed; packaged
source hashes match the build worktree and artifact SHA-256 is recorded.

The IRQ harness mocks hardware registers; it cannot prove bus timing, audio
quality, or Lexus behavior. Still-image artwork offset is zero; unsupported
metadata types are rejected. The implementation serves the observed request,
not every optional iAP command. PB35 remains installed until installation is
explicitly requested.

Protocol references and observed requests: PB35-LEXUS-PROTOCOL.md.
Recovery reference: Linux DWC2 incomplete-isoc-IN endpoint disable/completion
flow, adapted to RodBox's existing batch pump rather than copied wholesale.

## Publication status

Installed and tested: noise and accelerated playback time; superseded by PB37. Source reconstructed from the saved cumulative PB35-based patch and verified against build source hashes. Native builds are historical; host regression tests are rerun on final published source. Music inventories and filesystem checks are not full-library checksum verification.
