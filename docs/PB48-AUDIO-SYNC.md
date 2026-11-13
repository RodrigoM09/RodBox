# PB48: declare the USB audio clock model and expose token indications

PB47 kept startup packets available for a full polling interval, but the hardware test still showed no successful completions. The filesystem passed. Those traces cannot establish whether the host sent IN tokens while the packet was available.

The iAP AudioStreaming endpoint advertised bmAttributes=0x01 (no synchronization type). The PCM sender instead produces a fixed amount per 1-ms service interval: 192 bytes at 48 kHz, 128 at 32 kHz, and nine 176-byte packets plus one 180-byte packet per ten intervals at 44.1 kHz. PB48 explicitly declares synchronous ISO data (0x0d), matching this host-paced playback source rather than a free-running capture clock. Packet size, polling interval, supported rates and existing failure protections are unchanged.

[USB Audio Class 1.0](https://www.usb.org/sites/default/files/audio10.pdf), sections 3.3 and 4.6.1.1/Table 4-20, describes the audio synchronization types and their descriptor encoding. The previous descriptor omitted that declaration. Whether the Lexus rejects or refrains from polling because of it remains a hypothesis; this build is not proof of audible playback.

A bounded driver diagnostic records raw ISO IN interrupt flags and frame numbers before acknowledgement. It excludes software-disable-only and FIFO-empty-only events, preserves the budget for token/completion/error indications, and writes no controller registers. At most eight entries are recorded per endpoint setup. This helps distinguish missing host activity from delivery/completion problems in the next test; absent indications alone do not prove absent electrical bus tokens on this core.

Validation: all 28 USB scripts passed. The compiled descriptor regression fails against PB47 and passes against PB48. The production logger harness checks bounds, flags, excluded endpoints/events and unchanged registers. Native ipod6g/64MB build, image checksum, artifact hashes and tracked-source identity passed.

Built only: no installation, device writes or music changes. Lexus audio and clean post-test filesystem remain hardware acceptance requirements.
