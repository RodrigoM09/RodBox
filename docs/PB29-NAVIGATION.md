# PB29: Menu returns from Now Playing to Music

PB29 (`rodbox-pb29-wpsback-261030`) changes the short Menu action in Now Playing for playback entered through the regular Music browser. It retains PB28's filesystem cleanup and all preceding firmware improvements.

| Entry route | Menu in Now Playing |
| --- | --- |
| Music → Artist → Album → Song | Return to that album's saved song list and selection |
| Main menu → Now Playing | Return to the main menu |

## Implementation and scope

The iPod Menu-release mapping already produces `ACTION_WPS_MENU`. That action previously always returned `GO_TO_ROOT`. It now calls `root_menu_wps_back()`: a saved `GO_TO_DBBROWSER` origin returns `GO_TO_PREVIOUS`, while other origins retain the existing root return. The root dispatcher and Music browser already save/restore the previous screen, browse depth and selected item. Choosing Now Playing from the main menu resets the origin to the root, so it cannot accidentally return to an old Music list.

This deliberately covers the regular Music route. Other entry points preserve their prior behavior, including one-shot album-cover track-list routes that cannot safely be resumed by dispatching their screen identifier alone. The change does not stop playback, change tags, rebuild the database or rewrite artwork. The implementation changes `apps-ipod/root_menu.c`, its header and `screens/playback/wps.c`; the source version label is updated separately.

## Recorded validation

- Reviewed the physical Menu mapping, Music's saved depth/selection, dispatcher previous-screen restoration and main-menu origin reset against the active `apps-ipod` source.
- Native ipod6g / S5L8702 / 64 MB build passed with Arm GNU Toolchain 13.2.Rel1. All 40 codecs match PB28 byte-for-byte.
- Installed with a verified PB28 rollback backup. All 42 firmware files and 56 artist-image sidecars matched after installation/remount; backed-up database/settings/artwork files were preserved and the filesystem was clean.
- Music inventory, sizes and timestamps were unchanged. No full audio checksum pass was repeated for this navigation change; no music-file edits, formatting, filesystem repair or bootloader update were performed during this installation.
- PB28's 47-suite result is preceding evidence, not a claim that the entire suite was rerun for PB29. PB28's cleanup regression was rerun for publication and remains unchanged.

| Local build evidence | Value |
| --- | --- |
| Core bytes | 1,995,588 |
| Core SHA-256 | `acb3246f14512a4b528aefa308bf2232f31cf761d26a1c593adcdf3a7597098a` |
| Source checkpoint | `checkpoint/pb29` |

The private binary is not published; paths/dates/toolchain inputs may affect rebuild hashes.

## Pending device check

PB29 has been installed and safely ejected, but its startup and navigation have not yet been confirmed by the user. Restart with Hold off and confirm PB29. Select a song through Music → Artist → Album, then press Menu and check that the original song list and selection return. Back out to the main menu, select Now Playing, and check that Menu returns to that main menu. Reconnect for a read-only filesystem check after normal playback/artwork use.

Installation-time checks ran under PB28 until restart; they are not PB29 runtime acceptance. See [PB28's evidence limits](PB28-ARTWORK-CLEANUP.md) and [TESTING.md](TESTING.md).
