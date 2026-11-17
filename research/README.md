# Research and promoted experiments

The iFlash ATA-model detector was initially staged as uninstalled research. PB24 promoted a local adaptation into the firmware, alongside the generic SSD hints and explicit storage-mode overrides; PB26 retains it. The idea is credited to [Schattenruf/rockpod abbdc20](https://github.com/Schattenruf/rockpod/commit/abbdc2052804d1a5c5789f7ce04c4b2f2df9e6aa).

PB24 also adds a half-second settling delay on the non-PM ATA sleep path and retains adapter power during idle; it does not relax battery protection. Detection and power-policy regressions use mocked hardware and do not prove the physical root cause of corruption. See [current evidence](../docs/PB24-PB26-STATUS.md). Other candidates in this directory remain research unless explicitly identified as shipped.
