# Verification and its limits

## Focused tests

From the repository root:

```sh
python3 -m unittest discover -s companion -p 'test_*.py'
python3 tests/usb/test_write_length.py firmware-source/firmware/usbstack/usb_storage.c
python3 tests/usb/test_endpoints.py firmware-source/firmware/drivers/usb-designware.c
python3 tests/playlist/test_guard.py firmware-source/apps-ipod/playlist/playlist.c
python3 tests/playlist/test_compare_benchmark.py firmware-source/apps-ipod/playlist/playlist.c
```

Host C harnesses require clang and use AddressSanitizer/UndefinedBehaviorSanitizer. External hardware services are mocked. They exercise the extracted active function bodies; they are not a USB bus, decoder or storage-device emulator. Never send deliberately malformed write traffic to a filesystem containing your music.

Recorded checks: 17 USB write-length/state/residue cases; 11 endpoint/IRQ/blocking-return cases; 21 playlist guard/queue/replay/capacity cases; 50,000 old/new insertion comparisons. Companion fixtures cover interrupted/failed copies, containment, source changes, existing-file preservation and rejection of incomplete scans.

The playlist comparison benchmark runs on the host, not on the iPod. One recorded 16,000+1,000-entry run gave approximately 1.36x prepend and 1.61x middle; append was essentially unchanged at this scale. Do not translate that into a battery or device-speed guarantee.

## Device acceptance sequence

Back up firmware/settings/progress first. Add one isolated change; build and run its focused tests. Install only matching required files, compare expected hashes, unmount/remount and compare again. Test normal disposable transfers around the build's USB buffer size (24 KiB on the recorded ATA build) and a multi-megabyte file. Flush writes, bypass host read cache where supported, and compare hashes after remount. Remove only the test files created for the check. Run read-only filesystem verification.

Safely eject, fully restart, then check music playback, queue order, shuffle from an audiobook, headset controls and audiobook resume. Reconnect and repeat normal USB/remount/filesystem checks under the newly running firmware. Installation-time transfer checks run under the old firmware until restart; do not label them post-reboot acceptance.

PB7–PB9 completed that sequence. PB10 completed host/build/install checks but post-restart physical and USB acceptance remained pending at publication. No calibrated analog-output test, noise-floor measurement, long battery comparison or comprehensive digital-dock validation was completed.
