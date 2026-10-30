# Source checkpoints and private recovery

Every PB version has an individual commit and checkpoint tag. PB5 records an experiment that was rolled back; its separate rollback checkpoint returns to PB4. Treat the stage record as authoritative for whether source is exact, reconstructed or evidence-only.

These public checkpoints intentionally omit personal device data. A complete private recovery copy should separately preserve the current firmware tree, matching codecs/themes/fonts, current and pending settings files, book progress, and your audio. Protect that backup locally; do not commit it here.

For a checkpoint that includes `BACKUP-PATHS.json`, resolve each manifest entry
through that map before falling back to `.rockbox/<relative path>`. Raw macOS
`._` metadata is stored under neutral `raw-metadata/*.bin` names because copying
its associated file can automatically rewrite a normal sidecar. Verify the
saved blob against `SHA256.json`; an automatically generated sidecar beside the
backup file may not contain the original bytes. Native firmware, configuration
and progress files keep their ordinary paths. A before-reference record points
to an earlier complete checkpoint whose saved files were reverified before the
next installation; retain both directories together.

On this build, `config.cfg.new` can be promoted at startup. Back up both it and config.cfg before a deliberate settings change; editing only the old file can be undone on next boot. Do not overwrite someone else's settings or book state with generic examples.

Build a chosen source checkpoint deliberately. Do not assume an old package, core-only backup or legacy bookmark format matches the current app layer. PodBox uses native per-book progress; old bookmark state is not an automatic interchange format. Preserve newer progress before reverting firmware.

Normal firmware recovery did not require formatting, Finder/iTunes restore, partition changes, SysCFG flashing or bootloader replacement. Those are separate operations. Stop on unexpected filesystem errors and diagnose rather than repeatedly copying into a damaged filesystem.

## Replacement storage and sector views

Separate, explicitly approved replacement-card formatting and layout correction occurred during PB25 testing. A reader and the iPod can expose different logical sector sizes; a layout verified through the reader alone need not boot through the player. Do not copy an old partition map or guess a disk number. Establish device identity, capacity and sector geometry first; formatting, partition repair and bootloader flashing require their own authorization. See [current recovery evidence](PB24-PB26-STATUS.md). No automatic format/repair procedure or private install script is shipped here.

The selected library restore and full post-repair checksum check completed under PB27. Later artwork-cache filesystem errors led to PB28; see [current evidence](PB28-ARTWORK-CLEANUP.md). Existing orphan-cluster repair was separately authorized, backed up and verified without formatting. Installing the firmware correction does not reclaim existing orphans. Resume any future interrupted copy only after checking the expected device and existing-file hashes, preserving the approved selection and settings/progress.

PB29 is a navigation-only update retaining PB28's cleanup fix. Its installation used a clean filesystem and preserved the PB28 rollback, library/settings and artwork; no repair or format was needed. PB29 startup and both Menu paths were later confirmed; later diagnostic-report cross-links led to PB30. See [PB29 status](PB29-NAVIGATION.md).

PB30 fixes stale-directory-entry exposure. Recovery first repaired the existing cross-links, then removed the duplicate disposable `unreadable.txt` / `unreadable.dat` records with clean checks between passes, and finally installed/verified PB30. Do not unlink cross-linked files before repairing their shared allocation: that can free storage used by another file. Backups preserved firmware, artwork, database, settings and progress; no formatting or music writes occurred. The first PB30 playback/artwork/shutdown/restart/reconnect passed. See [PB30 evidence and limits](PB30-DIRECTORY-END.md); the private installer is not published.
