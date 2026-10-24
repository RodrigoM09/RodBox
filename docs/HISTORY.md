# Source checkpoint history

All publication commits are new sanitized exports, not fabricated original commits. Every PB version has its own commit/tag. Raw private backups remain offline.

| Checkpoint | What changed | Evidence quality |
| --- | --- | --- |
| legacy-official-release | Record official Rockbox release baseline | firmware-evidence-only |
| legacy-folders-shortcuts | Record separate Music and Audiobooks browse shortcuts | generic-configuration-example |
| legacy-daily | Record pinned Rockbox daily lineage | upstream-reference |
| legacy-remote1 | Archive initial headset decoder correction | partial-historical-evidence |
| legacy-remote2 | Record second headset decoder iteration | partial-historical-evidence |
| legacy-remote-trace | Record trace-assisted headset diagnosis | partial-historical-evidence |
| legacy-remote3 | Preserve trace-informed remote3 source | preserved-source-export |
| legacy-main-menu | Archive initial folder-based main-menu patch | partial-historical-evidence |
| legacy-library-bookmark | Preserve database Music and latest-only bookmark source | preserved-source-export |
| legacy-rockpod-integration | Archive selected RockPod Cover Flow and flash changes | partial-historical-evidence |
| legacy-menu2 | Preserve legacy Update Now menu and storage integration | preserved-source-export |
| legacy-scrim-classic | Archive temporary Scrim Classic appearance adaptation | theme-export |
| podbox-upstream | Import pinned PodBox foundation with inherited credits | pinned-upstream-source-export |
| pb1 | Migrate to PodBox, native Scrim, library and audiobook features | artifact-based-reconstruction |
| pb2 | Add decoder-based multi-click actions and portrait lookup | artifact-based-reconstruction |
| pb3 | Normalize art-cache volume keys and refine the library menu | artifact-based-reconstruction |
| pb3-followup | Add missing icons and preserve corrected artwork presentation | artifact-based-reconstruction |
| pb4 | Add bounded artist-art fallback and RodBox title | verified-source-archive-export |
| pb5 | Try USB endpoint validation (later rolled back) | exact-saved-step-delta-rolled-back |
| pb5-rollback | Restore verified PB4 after supported filesystem recovery | verified-recovery-source-export |
| pb6 | Start a fresh music queue for explicit Shuffle Songs | exact-saved-step-delta |
| pb7 | Report unexpected USB write lengths as failed commands | exact-cumulative-step-export |
| pb8 | Reintroduce endpoint guards after accepted PB7 | exact-cumulative-step-export |
| pb9 | Reject invalid playlist insertion positions | exact-cumulative-step-export |
| pb10 | Move paired playlist index tails as overlapping-safe blocks | exact-cumulative-step-export |

Each checkpoint has a matching `checkpoints/<name>.json`. PB1–PB3 are validated artifact reconstructions; PB5 is explicitly rolled back; PB10 hardware acceptance remains pending. See BUGS-AND-LESSONS.md for failure/rollback context and CREDITS.md for the imported/inherited code chain.
