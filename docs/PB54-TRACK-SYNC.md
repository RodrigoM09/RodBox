# PB54 — reconcile current playback identity on the USB thread

## Status

Version `rodbox-pb54-track-sync-261115`, target ipod6g / S5L8702 / 64 MB. Corrected native build and all **36 USB test scripts** passed. Follow-up independent review passed; PB54 was installed, read-back verified and safely ejected. Lexus hardware acceptance remains pending. Do not interpret host checks as confirmation of the actual car display.

## Exact reported symptom

Lexus forward/back controls refresh title/artist/artwork. Natural end-of-song advance and iPod-button skip change the song and elapsed timer but leave the displayed metadata/artwork stale. Reconnecting shows the correct current song. Preserve the working PB53 digital audio path and all music files.

## Evidence and limits

The retained PB53 logs identify the installed version and show elapsed-time resets and new audio-attribute handshakes without track-index notifications. They have rotated into database enumeration, losing subscription setup. They do **not** prove the Lexus's actual notification mask or why callback-delivered identity events are absent. One database metadata enumeration failure was observed, but it has not been established as this refresh defect and was not bundled into this fix.

PB52 corrected replacement-queue identity/order, deferred artwork capabilities and rotated selection. The unpublished PB53 prioritized finite identity/artwork events over recurring time notifications. The user's subsequent in-car report shows those host fixes alone did not resolve the Lexus symptom.

## PB54 implementation

Add a subscribed-current-track reconciliation hook before deferred-capability processing on the USB tick. The platform copies metadata using the existing locked, buffered-only `audio_peek_buffered_track(&id3, 0)`, rechecks playback state and queue index/count around the snapshot, and compares the full path plus displayed queue index/count with the last observed identity. It queues normal track/artwork events even if a playback callback was missed. Different albums/artists reusing an index and count invalidate the queue before announcing identity. Connection initialization explicitly invalidates the previous observation before initializing the iAP context.

Stable playback does not repeatedly invalidate queues or reload artwork. Stopped, unavailable or changing snapshots are retried rather than committed as a new identity. No notification mask is overridden and no unsolicited response is fabricated. Existing audio-attributes ACK gating remains intact. The poll performs no file opens or artwork lookup; the existing deferred-capability path queries artwork after an identity event.

Changed production files from PB53: `iap/platform.c`, `iap/platform.h`, `iap/libiap/platform.h`, `iap/libiap/notification.c` under `firmware/usbstack`, plus the one-line identity reset in `usb_iap.c`. PCM, USB audio controller/descriptors, playback implementation and all 40 codecs are unchanged. These selected baseline files were hashed; this was not a full unchanged-source-tree hash audit.

## Verification

`tests/usb/test_iap_track_state_sync.py` compiles the production USB notification tick and platform snapshot function with controlled playback/transport seams. It fails on preserved PB53 sources and passes on PB54 under ASan/UBSan. It covers callback absence, path changes at equal queue index/count, artwork-to-no-art, stable/stopped/resumed playback, failed/changing snapshots, DisplayRemote-only and ExtendedInterface-only subscriptions, and ACK gating. The retained asynchronous HID starvation regression remains separate, with only its new platform-hook seam stubbed. The new snapshot test itself does not emulate a real Lexus or the whole HID bus.

The first candidate was blocked before installation because review found that `audio_current_track_copy()` can perform playlist/tagcache fallback I/O. It was replaced with the already-existing buffered-only accessor; new tests forbid the non-buffered accessor and exercise pause, stop-during-copy and reconnect initialization. `test_iap_buffered_snapshot.py` compiles the actual native buffered function with no fallback dependencies available and checks unbuffered/missing metadata, pending skips and balanced locking. No playback implementation changes were needed. The rejected candidate and review are preserved privately.

The native build succeeded using the same Arm GNU 13.2.Rel1 version. The former compiler files were also dataless; the official Darwin-arm64 archive was fetched over verified HTTPS and matched Arm's published SHA-256 `39c44f8af42695b7b871df42e346c09fee670ea8dfc11f17083e296ea2b0d279`.

Image header/checksum/version and all 42 package files were verified. Core SHA-256: `3a2a18cd95b50a6d4ce5fa68fdc32b7367288da505338e5eecd0f6cf1b2066d7`. All 40 codecs match PB53 byte-for-byte. Before installation, 2,243 music entries matched inventory/size/mtime; no music writes or repeated full-content scan.

## Local continuity and acceptance

The Documents checkouts and even new evidence files became dataless/unreadable during this run. They were preserved, not overwritten. Canonical checkout is the active profile's `projects/rodbox-pb54`; private artifacts/backups are `projects/rodbox-pb54-artifacts`. Do not let Git silently operate in an ancestor home repository. Raw device logs, personal databases, backups and music are not published.

After guarded installation, check natural advance, iPod next/back, another album and artist including same-size queues, artwork-to-no-art, Lexus next/back, and continuous audio without reconnecting. If unresolved, collect startup/subscription traffic and stable playback identity evidence; do not continue speculative queue-order changes. Keep the PB53 recovery backup verified before any separately approved rollback.

## Approved installation — 2026-11-15

Installation verified all 42 firmware files; only core/info changed. 1,370 protected files were backed up and verified, database structures and 765 cache-image structures passed, and pre/post read-only filesystem checks passed. Inventory/size/mtime stayed unchanged for 2,243 music files; no music writes, repairs, formatting or repeated full-content scan. Private recovery backup: `PB53-before-PB54-20261115-095707`. Image SHA-256: `3a2a18cd95b50a6d4ce5fa68fdc32b7367288da505338e5eecd0f6cf1b2066d7`. The existing unused-partition-space advisory was left unchanged; both FAT checks returned exit code 0. Current private evidence is PB54-install-verification.json in the canonical artifact directory. No raw logs, backups or device identifiers are published.
