# PB52: refresh queue identity and artwork after album/artist changes

Version: `rodbox-pb52-track-refresh-261114` (ipod6g / S5L8702 / 64 MB).

## Changes

1. `apps-ipod/playlist/playlist.c`: announce the completed playback queue before starting it, outside the playlist write lock. Directory/M3U replacement queues did not previously announce their final contents. A different album can reuse both the old queue count and track index.
2. `firmware/usbstack/iap/libiap/notification.c`: send subscribed playback-engine-contents notifications before track-index notifications so the accessory invalidates cached queue-relative identities first.
3. `libiap/context.h` and `libiap/notification.c`: mark artwork capabilities for refresh on each track event, including reuse of the same index. Resolve them on the USB periodic tick, not the playback callback. Emit subscribed DisplayRemote TrackCaps and ExtendedInterface TrackCapsChanged packets. Do not keep polling after a successful refresh; defer through audio-attribute negotiation and preserve send backpressure.
4. `firmware/usbstack/iap/platform.c`: convert the accessory's display-relative selected-track index to the underlying rotated queue index before calling `audio_skip()`. Metadata and artwork already used this rotation; selection did not.

The PB51 USB audio controller driver, USB descriptors, PCM sink and codecs are unchanged. No music, tags, filenames or library structure are rewritten by this firmware installation.

## Evidence and tests

Three new host regressions exercise production C code, compiled with AddressSanitizer and UndefinedBehaviorSanitizer:

- `test_iap_queue_refresh.py`: replacement queue announcement before playback, including equal-sized albums/artists and reused track zero.
- `test_iap_notification_refresh.py`: real notification layouts, queue-before-index ordering in both lingoes, artwork present-to-missing transitions at a reused index, subscriptions, backpressure, attribute negotiation and no repeated successful capability polling.
- `test_iap_queue_identity.py`: metadata, artwork folder and selected track agree across all positions/rotations of a three-artist queue; invalid bounds, artwork-off and stopped lookup cases.

Each regression failed on its relevant PB51 production implementation before its correction and passed afterward. All **33 USB test scripts** pass, including PB51's same-buffer startup-recovery regression. Native core/codecs build, `ip6g` target, leading image checksum, embedded version and the 42-file SHA-256 manifest pass. The 40 codecs are byte-identical to PB51.

The build uses the existing native PB51 tree. Its pre-change core matches the known PB51 image hash; the four changed files were checked against the public PB51 sources. The full unchanged native source tree was not rehashed. Unchanged iAP C files and the audio controller/core/descriptor files were compared with the recorded pre-edit hashes.

Fresh PB51 logs were preserved privately with hashes. They confirm successful ISO audio completions after startup retry and sustained stream-byte consumption. The retained main logs had rotated into database enumeration; the actual album/artist-change requests and notification subscriptions were no longer retained. These source defects and host regressions are verified, but they do **not** prove Lexus hardware acceptance.

## Hardware acceptance still required

After the verified installation and safe eject, test in the Lexus with Hold off:

1. Confirm audio and information/art on the first selected album.
2. Skip within that album.
3. Select another album, preferably one with the same track count and starting index.
4. Select another artist; test both artwork-present and artwork-missing tracks.
5. Confirm displayed title/artist/album and artwork follow the playing track, then test pause/resume and reconnect.

Preserve fresh logs before long browsing sessions rotate the relevant packets away. Do not change the working PB51 audio driver based solely on a display failure.

Installation/build outcome is recorded in `checkpoints/pb52.json` and `docs/VERIFICATION.json`; in-car acceptance must remain pending until actually observed.
