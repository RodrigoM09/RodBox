# Analyze Music Now (PB11 test build)

The main-menu action updates PodBox's existing on-device sound index. It does
not initialize the music database, download music, change EQ or run a neural
model. Run **Update Now** first after adding music, wait for the database update
to finish, then use **Analyze Music Now** while connected to power.

The analyser asks before stopping playback and lets you choose Quick or
Thorough. Thorough is the better starting point when tonal/rhythmic matching
matters. A scan occupies the codec and stops playback. During its run the player
uses charging mode; ordinary USB file access returns when the scan exits.
Interrupted work can resume. The first library scan can take hours; runtime and
battery impact have not been measured for this build.

## What PB11 improves

- **Quiet signals:** the old power-to-decibel conversion discarded signals below
  approximately -48 dBFS before taking the logarithm. The corrected fixed-point
  calculation retains quieter measurements instead of reporting the silence
  floor. This is an RMS level measurement, not perceptual LUFS loudness.
- **Stereo energy:** level now uses mid plus side energy. Out-of-phase channels
  no longer cancel into a false silent level. Crest uses the largest channel
  sample peak; side-only audio reports maximum width. This does not claim to
  solve phase cancellation in the separate spectral/chroma pipeline.
- **Tempo reliability:** losing a beat lock clears its stale tempo and settled
  state. A changed tempo must hold again before being marked settled. This
  corrects confidence lifetime, not the detector's underlying tempo algorithm.
- **Measured duration:** count decoded samples, including the last block, instead
  of subtracting potentially repeated block-start timestamps. Onset rates now
  use that measured duration. Sample-rate changes retain earlier duration.

These corrections reuse the existing PCM/hop pass, bounded accumulators and
fixed-point arithmetic. No extra audio decode pass or model memory is added.
They do not establish a measured speed or battery improvement.

## Existing measurements and compatibility

The file stays at its existing version and 64-byte record stride. One reserved
byte now identifies the measurement algorithm revision. Legacy files remain
readable; the next update remeasures legacy records once. Thereafter unchanged
tracks reuse their current measurements. Both the desktop soundscan tool and
player share the corrected code and revision. Older external tools that write
revision zero produce records the new analyser will remeasure.

The finished index is retained while an update is in progress. Cancelling does
not remove it. This does not guarantee survival of arbitrary hardware failure
or power loss; keep the normal device backup. No music database initialization
is needed for this algorithm upgrade.

The menu's persistent key is `music_analyze`. The supplied opt-in example places
it after `database_update`. Existing custom orders are preserved unless that
key is deliberately added through the menu editor or a configuration merge.

## Verification and next acceptance step

Host tests run the actual probe, fixed-point logarithm and sound-index code.
Synthetic signals cover quiet levels, channel phase, silence, full scale,
channel layouts, duration, onset-rate accounting and changing tempo-lock state.
Filesystem tests cover a readable legacy record, an interrupted/resumed upgrade,
same-key replacement and cache invalidation. Hardware-dependent hop, chroma and
beat-tracker inputs are controlled fixtures: these tests are not a listening
benchmark or a real decoder test.

The ipod6g native build passes. Installation files were verified after remount
and the filesystem checked. Complete private before/after backups were verified;
only the core, build information and main-menu configuration changed. Device
analysis, cancellation/resume and playback
acceptance remain pending until tested on the player. Neural music profiles and
the new dynamic station engine are separate work in progress and are not enabled
by this button.

The original measurement pipeline is Anthony Fletcher's PodBox work, built on
Rockbox's decoders and fixed-point library. RodBox adds the focused corrections,
revision-aware update and main-menu action described here; see CREDITS.md.
