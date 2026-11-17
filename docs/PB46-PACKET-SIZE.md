# PB46: match the audio endpoint to its advertised packet size

PB45's Lexus test still recorded no successful audio completion, despite the matching sample-rate command arriving before retries exhausted. The filesystem passed and the audio log contained no playback-control assertions.

The iAP endpoint allocation programmed MPS=1024 while its USB audio descriptor and staging buffers use AS_PACKET_SIZE=192. The PB45 endpoint register trace confirms the 1024-byte hardware configuration. PB46 uses the shared AS_PACKET_SIZE constant for allocation as well, keeping controller configuration, advertised packet size and buffers consistent. The old 1024-byte allocation also exceeded the full-speed ISO maximum of 1023 bytes. The HID endpoint, storage endpoints, retry budget, PCM failure protection, rate recovery and log persistence remain unchanged.

This corrects a concrete configuration mismatch. The trace alone does not prove that the mismatch caused every unsent packet, and software tests cannot establish Lexus audio delivery.

Validation: the new test compiles the actual allocation and descriptor initializers. It fails against PB45 and passes against PB46, covering matching limits, full/high-speed legality, unchanged HID allocation and one-packet 44.1/48kHz payloads. All 27 USB test scripts pass. Native ipod6g/64MB build, image checksum, artifact SHA256 and tracked build-source identity verified.

Built only; no installation, device writes or music changes. Hardware acceptance requires successful audio completion logs, clean sound at normal speed and a clean filesystem after reconnect.
