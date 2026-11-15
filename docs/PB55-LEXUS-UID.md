# PB55 — honor the Lexus UID/artwork notification subscription

## Status

`rodbox-pb55-lexus-uid-261115`, ipod6g / S5L8702 / 64 MB. Native build and all **37 USB scripts** pass; independent review passed and PB55 is installed, read-back verified and safely ejected. Actual PB55 Lexus acceptance remains pending. The user reports PB54 still has the skip-refresh issue; **natural song completion was not retested**, so its physical outcome remains unknown.

## Log-supported cause

Unlike earlier rotated captures, fresh PB54 logs retain two startup sessions with identical subscription requests:

| Request | Raw payload | Meaning relevant to this bug |
| --- | --- | --- |
| DisplayRemote SetRemoteEventNotification | `00 00 01 8d` | Time/status/etc.; **no track-index or artwork-capability event** |
| ExtendedInterface SetPlayStatusChangeNotification | `00 00 09 01` | Basic + **TrackUniqueID** (request bit 8) + **TrackCapsChanged** (request bit 11) |

PB54's `play_stage_change_notification_set_mask_to_type_mask()` silently omitted both UID and caps bits while acknowledging the request. There was also no UID notification sender. Thus the Lexus did not receive the track-identity event it actually requested; sending/prioritizing index events could not help because those were not subscribed. The timer still updated through the requested DisplayRemote time events. Retained traces show Lexus PlayControl followed by explicit current-index, text and artwork queries, explaining why vehicle-button skips refresh independently of unsolicited identity events.

This is a captured configuration/implementation mismatch, not a newly assumed callback-loss theory. The earlier host tests used selected index/capability subscriptions rather than this real startup mask, so they did not cover this causal path. Raw logs, authentication traffic and personal track data remain private. A minimal sanitized mask fixture is published.

## Minimal correction

- Decode the requested UID and capability bits into their actual event-type bits without forcing index events or changing the subscription.
- Add type `0x0A`: **one type byte + eight big-endian UID bytes**, sent before recurring time traffic.
- On the existing buffered USB-side identity check, obtain the UID from `iap_library_key(path)`, exactly the stable key already used by metadata/database responses. Do not derive IDs from queue slots or change the hash algorithm/music files.
- Include UID-only subscriptions in the buffered reconciliation gate. Existing capability notification, queue ordering, reconnect reset and audio-ACK gating remain intact.

Five production files change: `iap/libiap/iap.c`, `iap.h`, `notification.c`, `notification.h`, and `iap/platform.c` under `firmware/usbstack`. Audio controller, USB transport/descriptors, PCM, playback implementation and all 40 codecs are unchanged.

## Verification and limits

`test_iap_lexus_uid_subscription.py` replays the captured four-byte subscription through the production command branch and mapper, then compiles the production buffered poll, notification sender, canonical path-key implementation and asynchronous HID send/completion code with controlled playback/transport seams. It fails on preserved PB54 at the decoded-mask assertion; mapping-only correction still fails because the UID sender is absent; the full PB55 correction passes under ASan/UBSan.

Assertions cover exact UID/caps payload bytes, no unrequested index event, local/callback-free track changes, another artist at equal queue index/count, artwork-to-no-art, stable state, UID-only subscriptions, canonical path/case aliases, unsubscribe behavior and backpressure. The callback-free sequence models automatic advance; it is **not** a physical end-of-song test or full Lexus emulator. All 37 USB scripts pass and the native build has no warnings/errors.

All 42 package hashes, model header/checksum and embedded version passed. Core SHA-256: `fbd1b155e6b3a8d9cb91877214b72608b96ef1912cce2ae2146bb6d52fac7920`. All 40 codecs match PB54 byte-for-byte. Fifteen selected native source snapshots establish the baseline; the full unchanged tree was not rehashed.

## Acceptance

After guarded installation, test iPod-button skips, another album/artist, then separately let a song finish naturally. Confirm title/artist/artwork and uninterrupted audio without reconnecting; verify Lexus-button skips still work. Expected new trace: ExtendedInterface PlayStatusChangeNotification type `0A` and `0D`, followed by the Lexus's refresh requests. New UID-based request types, if any, must be assessed from the resulting trace rather than speculatively bundled now.

Canonical checkout remains active-profile `projects/rodbox-pb54` on `community`; current private artifacts/backups are sibling `projects/rodbox-pb55-artifacts`. Older checkpoint source is pinned by tags; the versioned directory name is not the selected build. Documents originals remain preserved/unreliable. Preserve PB54 and new logs before any separately approved rollback. No music writes, formatting or repairs are authorized by this firmware installation.

## Approved installation — 2026-11-15

All 42 firmware files read-back verified; only core/info replaced. 1,370 protected files backed up and verified; database and 765 cache-image structures passed; pre/post filesystem checks passed. 2,243 music entries retained inventory/size/mtime. No music writes, full-content rescan, repairs or formatting. All 40 codecs and working audio/controller/PCM/descriptors/playback sources are unchanged. Private PB54 recovery backup: `PB54-before-PB55-20261115-103146`. Core SHA-256: `fbd1b155e6b3a8d9cb91877214b72608b96ef1912cce2ae2146bb6d52fac7920`. The existing unused-partition-space advisory was left unchanged; both FAT filesystem checks returned exit code 0. Safe ejection and disappearance of the mount were independently checked. Current private installation record: PB55-install-verification.json in the canonical artifact directory.
