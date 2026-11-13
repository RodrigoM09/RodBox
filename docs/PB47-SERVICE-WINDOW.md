# PB47: preserve the first packet for a full polling interval

PB46 confirmed the corrected 192-byte endpoint configuration, but its startup attempts still ended roughly every 125 microseconds with a DMA-loaded, unsent packet. No successful completion was recorded. Playback control acknowledgements succeeded and the filesystem passed.

The iAP high-speed descriptor advertises bInterval=4, or eight microframes (1 ms). Startup does not yet know the host's polling phase. The recovery code nevertheless treated the guessed next microframe as the expiry deadline and cancelled the FIFO packet at the first incomplete interrupt. PB47 separates this initial service-window deadline from the parity target: on S5L8702 high-speed startup, recovery waits until the target plus seven microframes. Each bounded re-arm therefore leaves the same packet available for a full service interval. The maximum remains eight re-arms, without fetching fresh PCM on failures. Established streams retain their existing known-phase policy; full-speed and other targets retain their previous timing.

This addresses premature software cancellation as a candidate cause, not proof of successful delivery. Hardware must confirm that the controller retains and sends the pending packet through the extended window. No USB descriptor, playback-control, storage or logging change is included.

Validation: all 27 USB test scripts passed. The expanded production recovery harness checks all 16,384 counter positions, the seven early microframes, expiry at the interval boundary, wraparound, full-speed/established-stream behavior and existing retry/ownership protections. It fails against PB46 and passes against PB47. Native ipod6g/64MB build, image checksum, artifact hashes and tracked-source identity verified.

Built only: no installation, device writes or music changes. Next acceptance requires successful audio completions, clean sound at normal speed and a clean filesystem after reconnect.

Reference: DesignWare-family incomplete-IN interrupts describe a transfer unfinished in the current frame, not completion of an arbitrary endpoint's entire polling interval. [ST controller training, interrupts](https://www.st.com.cn/content/ccc/resource/training/technical/product_training/group0/84/9d/da/d9/5e/7e/4d/9f/STM32MP1-Peripheral-USB_On-The-Go_Full_and_HighSpeed_interface_OTG/files/STM32MP1-Peripheral-USB_On-The-Go_Full_and_HighSpeed_interface_OTG.pdf). This is a related-core reference; the iPod hardware test remains necessary.
