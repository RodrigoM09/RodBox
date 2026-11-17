# PB14: wake the screen when power is connected

Status: installed after the sound-analysis scan finished. Verified before/after
firmware, settings and progress backups were retained privately. Physical
charger/computer wake and post-restart acceptance remain pending.

The accompanying theme follow-up moves Now Playing's battery display to the
same top-right position as the menu. That WPS file is installed with PB14.
The battery setting and the detailed USB footer remain unchanged. The requested
main-menu order places Now Playing before Update Now and Analyze Music Now.

When the running firmware sees its external power input change from absent to
present, it requests a normal backlight wake. This covers a USB charger or a
computer, including a full battery or a source not yet qualified as a charger.
The cached input is updated first, so consumers see the new power state before
the queued wake is processed.

Continued power does not keep requesting wakes. A later change in charging
qualification, battery-presence flags or charging activity does not create a
new plug-in wake. After removal, the next connection can wake it again.

The change uses the existing non-blocking backlight request. It adds no theme
rendering, filesystem work or delay to USB enumeration. Existing backlight
timeouts and hold/ignore policies remain in force. It does not change charging
current, battery calibration, idle shutdown, the bootloader or powered-off boot
behaviour. This is a backlight wake while RodBox is running.

## Validation and installation gate

The ipod6g native build passes. Fifteen ASan/UBSan cases execute the actual
power-input update helper with controlled inputs, checking USB/main connection,
unchanged input, full-battery/charging-qualification flags, removal/reconnection
and updating cached state before posting the wake. These are host state-machine
checks, not a charger, PMU or USB bus simulation.

Fresh verified before/after backups surround installation; only the core,
matching build information, Now Playing skin and menu-order setting changed.
The completed analysis index and audiobook progress remain intact.
Next, test a dark screen connected to
a charger, let its normal timeout expire without repeated waking, unplug and
reconnect, and repeat with the computer. Verify ordinary USB transfers after
restart. These hardware checks remain pending.

The power manager and backlight machinery are Rockbox/PodBox foundations. This
focused connection-edge change, tests and notes were developed for RodBox with
AI assistance, retaining the source's existing GPL notice.
