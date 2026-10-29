# RodBox

A documented, AI-assisted integration of Rockbox, PodBox, selected RockPod ideas and focused upstream fixes for a flash-modded iPod Classic.

RodBox is built on the work of the Rockbox community, Anthony Fletcher's PodBox, Nux Li's RockPod and the other contributors listed in [CREDITS.md](CREDITS.md). It combines their work with local adaptations, regression tests and a checkpoint-by-checkpoint development record. It is not a firmware written from scratch, and upstream features are credited to their original projects.

## What is in this version?

- PodBox's `apps-ipod` application layer: Music browsing, artwork rows/cache, native per-book audiobook progress and chapters, viewers and reorganized settings.
- Native Scrim with local volume-display, menu-title and icon adjustments.
- A Music / Audiobooks / Now Playing / Update Now / Analyze Music Now / Settings / System menu when the supplied menu order is applied. **Update Now updates the music database, not the firmware.** Analyze Music Now opens the on-device acoustic analyser; see [analysis and its limits](docs/NATIVE-ANALYSIS.md).
- Trace-informed headset-button decoding, bounded volume events and single/double/triple-click actions adapted around that decoder.
- Storage-mode transition safeguards that wake using the old mode before switching.
- A Shuffle Songs correction that starts a new music queue when coming from an audiobook, while preserving ordinary queue/replace behavior.
- Narrow upstream USB write-length/error and endpoint guards, a playlist insertion-position guard, and a small paired block-tail insertion optimization.
- Independently implemented Mac-side verified-copy and read-only library-health helpers.

The target used was **ipod6g / S5L8702 / 64 MB RAM**, on a seventh-generation Classic with flash storage. The Rockbox target name does not mean the physical device was a sixth-generation model. This is not a promise of compatibility with every Classic, adapter, headset or dock.

## Current status

Latest experimental source checkpoint: **PB26** (`rodbox-pb26-dbbootstrap-261028`). It preserves the [PB20–PB23 durability work](docs/PB20-PB23-DURABILITY.md), adds PB24 iFlash power handling and PB25 USB endpoint protection, and fixes initial Music database commits on memory-constrained players. All 45 host suites passed again on 2026-10-29. On-device startup, database creation, Music-menu playback and subsequent album hashes/filesystem checks passed. The larger music restore is **incomplete and paused at the user’s request** after completed batches passed verification and the player was safely ejected. [PB24–PB26 notes](docs/PB24-PB26-STATUS.md) separate confirmed results from remaining uncertainty; no permanent corruption fix is claimed.

`main` remains the locked stable reference; `community` carries these experimental source checkpoints. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Branches

`main` is locked read-only as the stable reference. Work goes to `community`: approved collaborators can push there, and everyone else can fork and send a pull request targeting `community`. Anyone can clone or pull the public code. Direct pushes require GitHub collaborator access; see [CONTRIBUTING.md](CONTRIBUTING.md).

## Explore and reuse

**Please feel free to take the parts you find useful, adapt them, or build on this version of Rockbox, while following each component's license and preserving its credits.** You do not need to adopt the entire firmware to reuse an individual fix or idea.

If you find a bug or a worthwhile improvement, please let the maintainer know through this repository's **Issues**. Pull requests are welcome too. Include the checkpoint/version, target hardware, steps to reproduce and what you expected to happen. Please remove personal paths, device identifiers, listening history and copyrighted media before attaching logs or examples. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Repository guide

| Location | Purpose |
| --- | --- |
| `firmware-source/` | Sanitized source export for the selected checkpoint; upstream notices remain in place. |
| `checkpoints/` | Public-safe stage records, reconstruction status and verification summaries. |
| `tests/` | Focused host regression harnesses with hardware services mocked. |
| `companion/` | Verified-copy and read-only health-report utilities plus synthetic tests. |
| `examples/` | Generic, opt-in configuration and folder examples; never a private device config. |
| `research/` | Uninstalled candidates explicitly marked as research. |
| [HISTORY.md](docs/HISTORY.md) | How the branches were pieced together and what each PB checkpoint changed. |
| [BUILD.md](docs/BUILD.md) | Target, toolchain and source-build instructions. |
| [BUGS-AND-LESSONS.md](docs/BUGS-AND-LESSONS.md) | Bugs, failed assumptions, rollback and evidence limits. |
| [PRIVACY.md](PRIVACY.md) | What is excluded and how the public Git history was checked. |

Each PB version has its own commit and `checkpoint/pbN` tag. PB5 is retained as a rolled-back historical experiment; a separate rollback commit restores PB4 before PB6. PB1–PB3 are labeled artifact-based reconstructions, not original independently preserved full snapshots. Original source dates and firmware versions are historical facts; the publication commits are newly created exports with neutral author metadata, not fabricated original commits.

No raw device backups, music, audiobooks, downloaded covers/portraits, personal library databases, playback progress or original build binaries are distributed. Git checkpoints are **source backups**, not complete device images. Some historical stages have evidence only rather than complete reconstructable source; their records say so.

## Build and verification

Read [BUILD.md](docs/BUILD.md), [TESTING.md](docs/TESTING.md) and [RECOVERY.md](docs/RECOVERY.md) before using a build. Back up your own settings and progress; do not mix a new core with incompatible old codecs/themes. The firmware updates do not replace the bootloader or flash SysCFG. Separate, explicitly approved storage recovery and replacement-card formatting/layout work occurred during private testing; those procedures and personal installation scripts are not shipped as part of a firmware update.

The firmware is predominantly GPL-licensed with separately licensed components. Scrim and bundled fonts have their own terms. See [LICENSE](LICENSE), [CREDITS.md](CREDITS.md), `firmware-source/docs/COPYING`, `firmware-source/docs/LICENSES` and the notices in individual files. AI assistance does not replace upstream ownership or licensing obligations.
