# PB16: protect USB storage from automatic idle sleep

Status: installed/backed up and booted normally; small USB checks passed, sustained writes still failed.

Review of a long-transfer failure found an idle-policy weakness. The power
manager blocks ordinary automatic shutdown while USB is connected, but that is
separate from the storage controller's power-saving policy. The Classic ATA
handler kept its storage timer routed during the USB storage session. When
idle, the flash policy could gate the controller clock and later remove flash
power. Turning off the backlight alone does not establish that storage slept.

There was also a stale-decision gap. The timer checked inactivity before taking
the ATA mutex. A sleep request could then wait behind a transfer, acquire the
mutex after that transfer refreshed activity, and sleep without rechecking the
new activity. The mutex prevents this path from gating storage halfway through
the protected transfer; the problem is the stale decision immediately afterward.

PB16 makes three focused changes to the existing Classic ATA driver:

- Latch USB storage ownership when its connect event arrives, before the
  storage thread acknowledges handover. While latched, automatic idle sleep,
  delayed sleep requests and deep flash power-down are inhibited. Disconnect
  refreshes the normal idle and deep-sleep grace periods.
- Recheck the inactivity deadline and ownership under the mutex before idle
  sleep. Recheck ownership, backlight and deadline under the mutex before deep
  power-down. Explicit shutdown sleep keeps its existing API and behavior.
- Return a failed transfer wake-up before preparing DMA or issuing data I/O.

The connect/disconnect events are the storage ownership broadcasts used by
`usb_request_exclusive_storage()` and `usb_release_exclusive_storage()`. Testing
only the final exclusive-ownership flag would miss the initial handover window.
The change does not keep storage awake merely because a charger is attached.
It changes no ATA hardware timing, PIO/DMA algorithm, USB acknowledgement order,
charging current, bootloader, partition layout or normal unplugged idle setting.

## Evidence and limits

The ipod6g native build passes. The actual policy, transfer and read/write
wrapper function bodies pass 33 scenarios in four host configurations, for
132 executions. These cover stale mutex decisions, USB handover, deep-sleep
rechecks, disconnect grace, tick wrap and failure before DMA/data activity.
See [the storage harness](../tests/storage/README.md) for mocks and limitations.
AddressSanitizer and UndefinedBehaviorSanitizer are enabled, except for the
explicitly documented pre-existing signed-shift error-code convention.

No sleep/wake trace was captured at the original failure. This fixes an
identified policy weakness; it does not prove the cause of that transfer error,
exclude a cable/adapter/card fault, or establish that all corruption is fixed.
An intermittent checksum mismatch, a later write I/O error and an inaccessible
firmware directory required recovery from verified private backups. Bulk USB
reliability remains under investigation. Do not treat host tests as physical
storage validation. Power loss, forced reset and physical disconnection remain
outside this guard's protection.

A new application core cannot change the bootloader already serving a recovery
USB session. It takes effect after a physical restart into the new core.
Installation-time transfers must not be reported as PB16 runtime acceptance.
Retain verified backups and perform normal transfer, remount, filesystem,
playback and resume checks after restart before accepting the build.

The driver and storage event framework are Rockbox foundations carried through
PodBox, with inherited RockPod flash sleep/wake adaptations credited in
[CREDITS.md](../CREDITS.md). This focused RodBox policy/error-handling fix and its
regression harness were developed with AI assistance and independent agent
review. Existing GPL notices remain intact.

Installation checks verified both complete firmware snapshots and the filesystem.
An intervening restart into the preceding build updated resume, playback and font
cache state; those differences were preserved and documented separately from the
two deliberately replaced core/information files. The preceding build was still
running during installation. A host power-log check found no full system sleep
during the later failing transfer; display sleep alone does not establish the
cause. Bulk-transfer acceptance remains pending after restart.

After restart, a normal-file USB probe passed, and all prior transfer checkpoints
passed fresh full readbacks. The next write failed with an I/O error; the
filesystem check then could not complete and the player was safely ejected.
The sleep-policy correction is insufficient to resolve current storage failures.
The separate [PB17 reset-lock correction](RESET-LOCKS.md) is prepared, not installed.
