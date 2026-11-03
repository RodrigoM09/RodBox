# PB35 Lexus investigation — 2026-11-02

PB35 installed and read-back verified; filesystem clean, database structure passed,
86 artist images and 765 cached images checked. 42 firmware hashes passed,
1,368 protected files checked, 2,243 music size/mtime records unchanged.
Full music hashing was not repeated. Normal safe ejection succeeded on retry.
Installed PB35 is unchanged by the subsequent source-only layout corrections.

## Metadata format cross-check

Independent sources:
- Hyundai controller request encoder and response decoder, commit
  270425b6f174ff95b90296ae03b0d2a3781a2dc8:
  https://github.com/suburbazine/hyundai-meego/blob/270425b6f174ff95b90296ae03b0d2a3781a2dc8/2015%20Genesis%20Source%20Code/src/debug/DHAVN_IPodController/extendedLingo/src/iTunesDbEngine/DHAVN_IPodController_getDBTrackInfo.cpp
  https://github.com/suburbazine/hyundai-meego/blob/270425b6f174ff95b90296ae03b0d2a3781a2dc8/2015%20Genesis%20Source%20Code/src/debug/DHAVN_IPodController/extendedLingo/src/iTunesDbEngine/DHAVN_IPodController_retDBTrackInfo.cpp
- Catplay generated protocol schema, commit
  fc52bac7910a07ff3b6d94712175db6013528aa9:
  https://github.com/catplay-labs/catplay/blob/fc52bac7910a07ff3b6d94712175db6013528aa9/core/catplay_lingo/src/lingos/lingo_0x4.rs

Both agree on a four-byte big-endian request index, four-byte count, and
response prefix of four-byte big-endian index plus one-byte information type.
Hyundai sends a one-byte mask; Catplay describes a four-byte LITTLE-endian
mask, explaining the Lexus's 12-byte request. PB35 captured mask bytes bf 20 00 00, meaning 0x20bf: capabilities, title,
artist, album, genre, composer, UID and album track index; count is one. This is implementation cross-verification, not a
direct reading of Apple's licensed specification.

Replies are separate per track/information type. Types 1..5 contain text;
type 6 duration is uint32; type 7 UID is uint64. The schema marks strings as raw_string (remaining payload); exact termination
semantics must be checked in its serializer before implementing text replies. Response does not contain a track count or a mask.

Corrected the unused local wire declarations: index/count were incorrectly
one byte each; mask was incorrectly represented as uint32_t[]; reply was
an unfinished request-shaped placeholder. Layout/fixture tests pass under
ASan/UBSan. These declarations alone DO NOT implement GetDBTrackInfo.

Implementation must stream replies through send-completion callbacks, bound
index/count without overflow, retain transaction ID, and resolve current
filtered database indexes. The global RAM database slot and playback queue
index are not interchangeable. iap_library_name uses block->entries[index].idx;
the new metadata accessor must follow that same selection without starting
playback. Do not advertise complete version 1.13 support prematurely.

## Audio evidence: correction to earlier hypothesis

PB34 usb.1.log at 824.081570 explicitly records the Lexus selecting 44100 Hz
with 44100 announced. Initial 48000 selection alone does not explain silence.
Playback state notifications also change after toggles, so not every command
is lost; PB35's completion acknowledgements will distinguish state failures.

At 824.081085 endpoint 0x81 starts once, but no subsequent audio throughput
records are present in the preserved interval. Driver GINTSTS 0x04108c28 has
bit 20 set (incomplete isochronous IN on this DesignWare core).
usb-designware.c notes these incomplete-iso bits are not enabled as interrupts;
usb_core.c's non-native batch pump advances on transfer completion only.
This is a plausible stalled-endpoint path, NOT a proven cause: the status
bit may be stale from the earlier interface activation. Inspect fresh PB35
endpoint start/completion logs before adding endpoint-reset recovery.

## PB35 hardware retest and next implementation work

Authentication succeeded. Play/pause acknowledgements followed state changes.
The host selected 44100 Hz, matching the announcement, but stream counters
reported zero music bytes/chunks and no elapsed-time movement. The incomplete
ISO IN condition and missing recovery handler remain the leading endpoint
hypothesis. Linux DWC2 also handles incomplete ISO IN interrupts explicitly:
https://code.googlesource.com/linux/torvalds/linux/+/7bcf809b1e7889ab7e75fe1fcf8f1a98332f36d2/drivers/usb/dwc2/gadget.c

The next audio change needs bounded endpoint-specific recovery and mocked IRQ
tests; do not reset the whole USB controller or alter storage endpoints.

GetDBTrackInfo (0x0040) requests track zero, count one, mask 0x20bf and is rejected.
GetTrackArtworkTimes (0x002a) is also rejected. The ten-byte request structure
already exists for DisplayRemote, but the ExtendedInterface dispatcher has no
case. Reusing that handler blindly would also inherit missing index/format
validation. Implement and test that validation together with the dispatch.

A category-8 count request returns zero (category not supported); it is distinct
from the failed metadata response. Do not label every diagnostic a failed
authentication.

The device name was a saved user setting, not the firmware version. It was changed
to RodBox!, read back and followed by a passing filesystem check. The generic
example is published; no private device configuration or logs are included.

Remaining: implement bounded metadata streaming using filtered database indexes,
validated artwork-time responses and endpoint recovery; then build and car-test.
No fixes for these remaining paths have been installed or claimed.
