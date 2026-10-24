# PB15: one battery indicator on the USB screen

Status: installed with verified recovery checkpoints. The previous complete
checkpoint was rechecked before installation; a fresh complete checkpoint was
saved afterward. Only the core and matching build information changed. Settings,
completed analysis and audiobook progress remain unchanged. Raw Mac metadata
sidecars are saved under neutral blob names with a path map, avoiding automatic
sidecar rewrites; every saved logical file is rechecked after copying finishes.
Private backup paths and contents are not published.

A USB connection made from Now Playing could show a small solid battery panel
over fragments of the old theme's battery and clock. The plain USB screen
deliberately retains the previous framebuffer around its message. Its 72 by 20
pixel indicator panel did not cover Scrim's 35-pixel header. Clearing a viewport
can also restore a backdrop instead of painting over it.

The USB renderer now paints the whole 35-pixel header with a solid fill before
drawing its single built-in battery indicator at the right edge. It retains
the icon/percentage/both preference and the detailed battery/power footer. The
previous theme clock is cleared on this screen; this change does not draw a
USB clock. Now Playing and menu themes retain their own normal presentation.

All drawing stays after the storage handover acknowledgement. It uses the
built-in font and ordinary framebuffer primitives, with no theme rendering,
font paging, artwork loading or filesystem access. Cached level/charging
changes still control repainting. The existing USB message and HID flow remain
unchanged. The implementation builds on Rockbox/PodBox's USB screen, retaining
its GPL notices; the focused fix and tests were developed with AI assistance.

The native ipod6g build passes. The actual renderer passes 24 ASan/UBSan
framebuffer cases covering all three display modes, charging states and
unknown/empty/half/full battery levels. The checks verify that stale header
pixels disappear, the centre is untouched, viewports are restored and unchanged
state does not repaint. A source-order assertion checks the first battery draw
follows the storage acknowledgement. These checks do not simulate the LCD
driver or USB bus. On-device visual and post-restart USB acceptance are pending.
