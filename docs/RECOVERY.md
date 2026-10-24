# Source checkpoints and private recovery

Every PB version has an individual commit and checkpoint tag. PB5 records an experiment that was rolled back; its separate rollback checkpoint returns to PB4. Treat the stage record as authoritative for whether source is exact, reconstructed or evidence-only.

These public checkpoints intentionally omit personal device data. A complete private recovery copy should separately preserve the current firmware tree, matching codecs/themes/fonts, current and pending settings files, book progress, and your audio. Protect that backup locally; do not commit it here.

On this build, `config.cfg.new` can be promoted at startup. Back up both it and config.cfg before a deliberate settings change; editing only the old file can be undone on next boot. Do not overwrite someone else's settings or book state with generic examples.

Build a chosen source checkpoint deliberately. Do not assume an old package, core-only backup or legacy bookmark format matches the current app layer. PodBox uses native per-book progress; old bookmark state is not an automatic interchange format. Preserve newer progress before reverting firmware.

Normal firmware recovery did not require formatting, Finder/iTunes restore, partition changes, SysCFG flashing or bootloader replacement. Those are separate operations. Stop on unexpected filesystem errors and diagnose rather than repeatedly copying into a damaged filesystem.
