# RodBox

A documented, AI-assisted integration of Rockbox, PodBox, selected RockPod ideas and focused upstream fixes for a flash-modded iPod Classic.

RodBox is built on the work of the Rockbox community, Anthony Fletcher's PodBox, Nux Li's RockPod and the other contributors listed in [CREDITS.md](CREDITS.md). It combines their work with local adaptations, regression tests and a checkpoint-by-checkpoint development record. It is not a firmware written from scratch, and upstream features are credited to their original projects.

## What is in this version?

- PodBox's `apps-ipod` application layer: Music browsing, artwork rows/cache, native per-book audiobook progress and chapters, viewers and reorganized settings.
- Native Scrim with local volume-display, menu-title and icon adjustments.
- A Music / Audiobooks / Update Now / Now Playing / Settings / System menu. **Update Now updates the music database, not the firmware.**
- Trace-informed headset-button decoding, bounded volume events and single/double/triple-click actions adapted around that decoder.
- Storage-mode transition safeguards that wake using the old mode before switching.
- A Shuffle Songs correction that starts a new music queue when coming from an audiobook, while preserving ordinary queue/replace behavior.
- Narrow upstream USB write-length/error and endpoint guards, a playlist insertion-position guard, and a small paired block-tail insertion optimization.
- Independently implemented Mac-side verified-copy and read-only library-health helpers.

The target used was **ipod6g / S5L8702 / 64 MB RAM**, on a seventh-generation Classic with flash storage. The Rockbox target name does not mean the physical device was a sixth-generation model. This is not a promise of compatibility with every Classic, adapter, headset or dock.

## Current status

Latest source checkpoint: **PB10**, `homepod-pb10-plmove-261024`. PB7–PB9 passed user playback/resume/control checks and post-reboot normal USB transfer/remount/filesystem verification. PB10 passed the native build, 21 guard tests, 50,000 differential cases and installation-time persistence/filesystem checks; its own post-restart hardware/USB acceptance remains pending at publication.

The small playlist optimization's Mac benchmark is not an iPod speed or battery measurement. Digital audio and accessory code inherited from PodBox is present in source but was not comprehensively exercised, and optional DAC/car modes were left off. Explicit iFlash-brand recognition remains staged pending actual ATA identification; existing generic flash detection may already cover the adapter. Legacy Rockbox games/plugins are not available through PodBox's replacement app layer.

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

Read [BUILD.md](docs/BUILD.md), [TESTING.md](docs/TESTING.md) and [RECOVERY.md](docs/RECOVERY.md) before using a build. Back up your own settings and progress; do not mix a new core with incompatible old codecs/themes. This project did not change the bootloader, format storage, flash SysCFG or replace the partition layout.

The firmware is predominantly GPL-licensed with separately licensed components. Scrim and bundled fonts have their own terms. See [LICENSE](LICENSE), [CREDITS.md](CREDITS.md), `firmware-source/docs/COPYING`, `firmware-source/docs/LICENSES` and the notices in individual files. AI assistance does not replace upstream ownership or licensing obligations.
