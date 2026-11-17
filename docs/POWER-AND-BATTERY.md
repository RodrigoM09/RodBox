# PB12: analysis power detection and visible battery state

PB11's first device test exposed a pause at "Connect the charger to continue"
despite an attached power source. The scan used `charger_inserted()`, which tests
the Classic's qualified charging-capability flag. The driver reports USB power
presence separately; a full battery or a source not qualified by its charging
probe can therefore leave that test false while power is connected.

PB12 uses the existing cached `power_input_present()` check for starting and
continuing analysis. Removing power still pauses it, reconnecting lets it
continue, and Stop/USB/shutdown controls retain their existing behaviour. This
does not alter current limits, charger probing, battery calibration or charging
hardware. Presence of a source is not a measurement of its available current.

The charging skin tag now follows the monitored charging signal on targets that
provide it. Scrim shows battery percentage and power/charging state beside Now
Playing's artwork, within the existing left margin. The menu shows connection
state under the clock. "USB"/"USB power" means connected, while "Charging"/"CHG"
means the monitored charging signal is active; a full connected battery need
not display Charging. Initial PB12 used Update Now's task glyph for Analyze
Music Now in Scrim's text-to-icon mapping.

The PB12 theme follow-up gives Analyze Music Now its own waveform glyph (`P`,
U+0050 in Scrim's bundled Material icon font), leaving Update Now unchanged.
The glyph was checked visually in the actual bundled font. This is a one-token
theme correction; it does not require a new firmware core or an analysis rescan.
It was prepared while the player's analysis was running; PB13 includes it with
the [selectable battery presentation](BATTERY-DISPLAY.md), which replaces the
theme's power text with the chosen icon/percentage layout. The detailed USB
battery footer is retained.

The computer connection screen shows battery percentage and Charging or USB
connected. Its small status viewport uses the built-in font, cached battery
level and a direct charging-state read. It starts only after the USB storage
ACK and repaints on a changed value during ordinary and HID idle polling. It
does not load skins, page fonts, read artwork or access files while the computer
owns the filesystem. No full-screen theme rendering is added to USB handover.

## Validation

- Native ipod6g build passed.
- Seven ASan/UBSan cases execute the actual scan power/abort functions with
  controlled inputs: connected power, removal, reconnection, stop and USB events.
- The current PodBox skin parser accepts both modified Scrim files, including
  their font and bitmap resources. Its host checker needed local build-only
  stubs for five unrelated UI callbacks absent from upstream's checker stubs;
  no such stubs are part of the device firmware.
- On-device analysis, battery-display appearance and post-restart USB acceptance
  remain pending. Parser acceptance does not prove visual layout or charging
  hardware behaviour.

The sound-measurement pipeline and Scrim remain Anthony Fletcher's PodBox work
on Rockbox. Scrim modifications retain its CC BY-SA 3.0 notice; source changes
retain their GPL notices. This correction and the host tests were developed
with AI assistance. Unfinished smart-station sources remain outside this build.
