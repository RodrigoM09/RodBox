# Read-only media-integrity investigation after PB55 acceptance

**PB55 hardware acceptance — 2026-11-15:** the user confirms the Lexus metadata/artwork refresh issue is fixed and natural song completion was tested successfully. A separate artist-collection early-ending report reproduces as damaged source content, not a confirmed firmware regression. PB55 remains the current firmware; no PB56 was built or installed for this finding.

## Evidence

A user-reported artist collection ended early. Strict independent host decoding of all 28 affected FLAC files reproduced 27 failures; one decoded cleanly to its declared end. Seven had zero-filled headers; sampled files had large zero-filled spans. The 28 corresponding mounted-source files are SHA-256-identical and produce the same decoder outcomes. The read-only FAT filesystem check passed. File sizes/timestamps and filesystem structure do not establish audio content integrity.

This is a media-content failure independent of the Lexus display fix. It does not establish when/how the bytes were damaged or diagnose a faulty card/adapter. Recopying the identical source would not recover audio. Isolated retained USB warnings do not explain the same offline source-file failure and do not justify altering the working pipeline.

## Safe outcome

PB55 remains installed. All 42 firmware files match the verified package; 2,243 music entries retained inventory/size/mtime. No firmware/music writes, repairs, formatting, or repeated full-library checksum. Only this 28-file subset was content-compared. No PB56 firmware, tag, or claim of a media repair was created. Sources remain unchanged; this publication updates evidence/acceptance documentation only.

## Next step

Obtain a different known-good original/rip/backup, validate full decoding and expected content before asking for a guarded replacement. Preserve current files and evidence. Do not blindly recopy the known bad originals, transcode away missing data, or conceal decoder failures. Private paths, track names, detailed hashes, logs and copyrighted audio are excluded from this repository.
