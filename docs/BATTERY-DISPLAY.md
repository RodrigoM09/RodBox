# PB13: selectable battery presentation

Choose **Settings > Appearance > Interface Elements > Battery Display**:

| Mode | Scrim top indicator |
| --- | --- |
| Icon only | Battery icon, with no percentage |
| Percentage only | Small numeric percentage, with no battery icon |
| Icon + percentage | Small percentage beside the battery icon |

The selected mode applies while on battery, charging or connected over USB.
Charging changes the battery glyph; it never controls whether the percentage
is visible. Scrim's menu percentage remains visible during volume adjustment.
Now Playing uses the same top-right battery coordinates as the menu: the icon
at x=289 and the combined percentage at x=249. Percentage-only mode aligns at
x=279. The follow-up corrects PB13's initial placement in the left margin. It
adds no opaque panel over album art and does not move the volume overlay.
The separate detailed battery/charging footer on the USB connection screen is
retained in every mode. That screen also follows the top-indicator preference
using plain drawing and the built-in font after the storage ACK, with no theme,
font paging or filesystem access during USB transfers.

The existing saved values `graphic` (0) and `numeric` (1) retain their meanings;
`both` (2) is added. Settings storage remains an integer of the same size, and
the default for existing users remains Icon only. A deliberate personal
configuration merge can enable `battery display: both`; do not replace an
existing configuration wholesale. Mode labels have English source/destination
and voice entries. The existing Battery Display setting remains in its current
menu and reloads the theme through its existing theme-setting behaviour.

The combined layout is implemented in Scrim and the plain USB screen. Other
themes need a third branch for the new setting value. The small legacy built-in
status bar has one battery cell and uses the icon for combined mode.

## Validation

The ipod6g native build passes. Both modified Scrim files pass the current
PodBox skin parser, linked with the updated three-choice settings table. In the
actual bundled 12-pixel font, `100%` is 27 pixels wide in a 34-pixel viewport;
the widest 12-hour clock string is 48 pixels in a 58-pixel viewport. Battery,
percentage, clock and title occupy separate areas. The new waveform icon for
Analyze Music Now is included; it was previously prepared while analysis ran.

Installed files and the enabled combined preference passed hash verification
after remount; read-only filesystem verification passed. These installation
checks ran before PB13's first restart. Appearance, changing all three modes,
persistence after restart and
post-restart USB acceptance remain on-device checks. No sound-analysis data,
media, audiobook progress or charging policy is changed by this feature.

Scrim is Anthony Fletcher's PodBox theme under CC BY-SA 3.0, using its existing
credited fonts/icons. Firmware remains based on Rockbox/PodBox under its
existing licences. The focused setting/layout changes and documentation were
developed with AI assistance. No new downloaded assets or neural model are used.
