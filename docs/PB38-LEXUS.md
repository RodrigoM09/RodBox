# PB38: host-token audio synchronization and missing-tag display fallbacks

Synchronize the first isochronous IN packet to a real host IN token rather than guessing its phase. Preserve the queued buffer while waiting; advance one interval per successful completion. Reset synchronization on cancellation/reset. PB37 fail-stop remains: failed or short transfers consume no new PCM.

The PB37 database snapshot contains genuinely untagged first entries in All Songs. Missing titles now use filenames, and other missing text fields have explicit Unknown labels. Known tags and music files remain unchanged. Failed playlist lookups no longer report success using stale metadata.

Validation: native ipod6g64MB build passed without compiler warnings. Eight focused suites passed: token synchronization (all HS microframe phases and wrap; FS cadence), ISO recovery, audio batch failure, filtered metadata including missing tags, metadata wire format, artwork times, playback rates, endpoint ownership. Tests mock hardware; Lexus sound and live track updates still require an in-car test.

The connected device's orphan clusters were repaired separately and its filesystem passed afterward. No formatting or music-file writes. Music inventory/size/mtime checks are not a full music checksum pass.

## Publication status

Installed and tested: nonempty metadata replies observed; Lexus audio and live track updates unresolved. Source reconstructed from the saved cumulative PB35-based patch and verified against build source hashes. Native builds are historical; host regression tests are rerun on final published source. Music inventories and filesystem checks are not full-library checksum verification.
