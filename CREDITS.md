# Credits and provenance

RodBox is a personal integration of existing open-source iPod firmware, selected upstream fixes, local adaptations and companion utilities. It is not an independently written replacement for Rockbox. The local integration, tests, documentation and debugging used OpenAI ChatGPT/Codex assistance; user-directed hardware checks provided a separate acceptance step. Passing a build or a host test is not proof of battery, audio-quality or universal accessory compatibility.

## Incorporated foundations

- **Rockbox and its contributors** — https://github.com/Rockbox/rockbox and https://www.rockbox.org/. Firmware, codecs, drivers, DSP, storage, playback, build system and documentation underpin the whole project. Earlier local work used Rockbox revision `bad21c5f52`. Retain `firmware-source/docs/CREDITS`, `firmware-source/docs/COPYING`, `firmware-source/docs/LICENSES`, individual file notices and component licence files.
- **PodBox by Anthony Fletcher** — https://github.com/anthonyfletcher/podbox, pinned base `0fe9c63355c4fc63e892237d019666fff4932a13`. The active application layer is `apps-ipod`. Native artwork lists/cache, in-memory music browsing, audiobook progress/chapters, viewers, settings organisation/search/explanations and rich theme rendering come from this foundation. These are upstream features, not new RodBox inventions.
- **RockPod by Nux Li / nuxcodes** — https://github.com/nuxcodes/rockpod. Earlier local work adapted selected flash sleep/wake and Cover Flow behaviour from inspected tree `951d17c0575fbb61f3c585b5f0c3a0a941dcb10f`; the Cover Flow interface was subsequently removed at the user's request. The current PodBox foundation itself credits RockPod as its starting point for the app layer, hardware and much serial accessory support. Local storage safeguards were adapted to PodBox. This is not an installation of all RockPod features.
- **Spun / Stats_for_iPod by Siebe Majoor / majorsiebe** — https://github.com/majorsiebe/Stats_for_iPod, credited by PodBox as inherited work. Retain PodBox's full credits and component-specific documentation for the complete inherited dependency chain.

## Selected upstream fixes and adaptations

| Source | Credit | Local scope |
| --- | --- | --- |
| [Rockbox `51fdc7f`](https://github.com/Rockbox/rockbox/commit/51fdc7f856bb5dd8e3cb3cfd95e36d5d1dbb08f0) | delacor; commit also credits Cursor | Exact queued USB write-length checking and failed-command status; PB7. |
| [Rockbox `72d1473`](https://github.com/Rockbox/rockbox/commit/72d147349741d5c419c364423ad615e6ca91507f) | Robin Tschirschnitz; committed by speachy; commit also credits Cursor | Reject unconfigured/inactive DesignWare endpoints and propagate errors; initially tried as PB5, rolled back during a filesystem recovery, later reintroduced as PB8. |
| [rockbox_optimised `c498fd6`](https://github.com/apolyaker92/rockbox_optimised/commit/c498fd6ca05bd8e13c72f403d88db88db1856385) | apolyaker92; commit credits Claude Opus 5.5 | Insertion-position guard adapted to PodBox's playlist engine; PB9. The removal guard was already present. |
| [rockbox_optimised `c4a761c`](https://github.com/apolyaker92/rockbox_optimised/commit/c4a761c6d28a3478de41368b9522609edfd9fc38) | apolyaker92; commit credits Claude Opus 5.5 | Research informed a small local paired `memmove` for playlist indices and dircache references; PB10. The upstream insert-gap architecture was deliberately not imported because the locking/yield assumptions differ. |

The original firmware file notices govern the adapted code: the touched USB storage and playlist files explicitly use GPL version 2 or later. The project includes GPLv2 text and independently licensed components. Do not replace all licences with a blanket new licence.

## Scrim and bundled fonts

**Scrim / Scrim_p**, created by Anthony Fletcher for PodBox: CC BY-SA 3.0. RodBox modifies volume presentation and selected icon mappings/title presentation; attribution and share-alike terms remain. See `firmware-source/themes/scrim/README.md` and its adjacent font licence files.

- Google Material Design Icons — Apache 2.0.
- Noto Project Authors — Noto Sans/Serif, SIL Open Font License 1.1.
- Evan Kenny / Dook and MicroNotoSans authors — the MicroNotoSans fork, SIL OFL 1.1.
- Douglas Vautour — Seven Fifteen, CC BY-SA 4.0.
- stgiga and GNU Unifont contributors — UnifontEX, licences described in `LICENSE-Seven-Fifteen.txt` including the font exception/OFL alternative.

If other upstream themes remain in the distributed source, preserve their own README, font licences and attribution too. Scrim's licence does not cover unrelated themes or downloaded album art.

## Independently implemented companion work and services

- **HifiMule** — https://github.com/HifiMule/HifiMule, reviewed tree `ca32adafa791bcb58b11cbe3ccf1a12851331973`. Its verified device-I/O/checkpoint design informed an independently written Python copy utility: contained paths, staged files, sync, verification and atomic replacement. No Rust implementation was copied wholesale.
- **rockbox-library-manager / cyberdeliaAI** — https://github.com/cyberdeliaAI/rockbox-library-manager. Its scan-safety/library-health approach informed an independently written, read-only manifest health reporter. This project in turn credits Anthony Fletcher's artwork fetcher. No GUI, reorganiser or automatic deletion workflow was imported.
- **Apple artwork search, Last.fm and TheAudioDB** — sources used to locate matching artwork for a private library. These are service/data acknowledgments, not firmware-code dependencies. Downloaded covers, artist photos, music and personal library manifests are excluded from this repository; copyright in those assets remains with their respective owners.
- **Mutagen** and **Pillow** — local media metadata and image tooling used during artwork preparation and validation. These Python packages are not part of the iPod firmware and should not be silently vendored.
- **Arm GNU Toolchain 13.2.Rel1** — compiler used for the native ipod6g builds; toolchain distribution remains separate.

The headphone preset is a conservative listening adjustment, not a calibrated correction of every headphone or ear. The preserved local implementation does not identify an exact downloadable measurement dataset sufficiently to claim one was imported; do not invent such provenance.

## Focused adaptations and remaining research

PB11's focused acoustic-analysis corrections and revision-aware refresh were
implemented for RodBox with AI assistance. The underlying PCM analysis,
beat/chroma pipeline, resumable sound index and soundscan tool are inherited
from Anthony Fletcher's PodBox; the decoders and fixed-point library are
Rockbox work. The new synthetic tests exercise those actual sources. No neural
model or third-party model code is included in PB11.

- [Schattenruf/rockpod `abbdc20`](https://github.com/Schattenruf/rockpod/commit/abbdc2052804d1a5c5789f7ce04c4b2f2df9e6aa): explicit iFlash ATA-model detection informed the local PB24 adaptation, now retained in installed PB26. Standard SSD hints and explicit mode overrides remain supported. PB24 power handling also references the iFlash report in nuxcodes/rockpod#37; neither attribution establishes a physical corruption root cause.
- Broader playlist batching/resume/unshuffle patches were reviewed, not included wholesale.
- UglyEgg/rockbox-music, bahusoid/rockbox, Nokikuji/NokiPod, tsirysndr/equalizer, stevenla/rockbox-ipod, Wuverul/SongDock, Pates2004/rockbox-accessible, dest92/Better-Rockpod, morgenman/RockBoxPersonalMods, deandromi/Rockbox-Rockpod-HFSPlus and brnomt/rockbox were research leads. They must not be described as installed firmware contributions without a specific later imported patch.

PodBox's inherited accessory and speech credits include Paul Sauro's Rockbox changes, mojyack/libiap, oandrew/ipod-gadget and ipod, iAP2 protocol research, NV Access's NVSpeechPlayer, Carnegie Mellon's CMU Pronouncing Dictionary and the credited NRL letter-to-sound rules. The full upstream README and `firmware-source/docs/podbox/iap-sources.md`, `firmware-source/docs/podbox/iap2-sources.md` and `firmware-source/docs/LICENSES` remain authoritative for that inherited material. Presence of source does not establish that every optional feature was enabled or tested on the target player.

PB24–PB26 follow-up work used Codex assistance for focused source review, regression harnesses, native builds and documentation. PB26’s Music database fix has an on-device check; host mocks and partial transfer success do not certify long-term storage reliability, battery behavior or headset controls. Upstream ownership and licenses remain unchanged.

PB27’s merge-buffer alignment correction and production allocator/insertion regression were prepared with Codex assistance. Existing duplicate database rows were repaired separately during approved private recovery, with per-track semantic preservation checks; those private records and scripts are excluded. On-device startup/artist presentation and post-startup integrity checks passed. This does not certify a permanent storage-corruption fix.

PB28's deferred-unlink cleanup correction and production-callback regression were prepared with Codex assistance. The underlying filesystem and artwork implementation remains credited to its original Rockbox/PodBox contributors. The regression uses mocked storage/bookkeeping; all 47 host suites passed and one physical restart/reconnect was clean. Personal media, artwork, device backups and repair scripts are excluded.

PB29's regular-Music/Now Playing return-path adjustment was prepared with Codex assistance using the existing PodBox/Rockbox browser and root-dispatcher state. Source review, native build and installation/remount checks passed. Physical PB29 startup and both Menu paths were subsequently confirmed; no new upstream code or media was imported.

PB30's FAT directory end-marker correction and production-function regression were prepared with Codex assistance. Rockbox's existing FAT implementation and its author/license notices are preserved. Eight focused suites and the native build passed, followed by one clean playback/artwork/shutdown/restart/reconnect cycle. No new external code or media was imported.
