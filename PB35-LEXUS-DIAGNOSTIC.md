# PB35: Lexus diagnostics and command acknowledgements

Installed and tested. Authentication succeeds; play/pause changes are acknowledged
after the state transition. Lexus audio remains silent and elapsed time stays
still. This is NOT a completed Lexus compatibility fix.

Changes: wait for play/pause state, reject overlapping pending transactions,
avoid acknowledging pause from sink startup, validate complete sample-rate words,
and log complete twelve-byte track-information requests. The direct synchronous
audio-control experiment was discarded because it could deadlock under the iAP
lock.

Native build and four focused host suites passed. Installed firmware hashes,
database, artwork and read-only filesystem checks passed. Music files were not
written; the install compared inventory, sizes and modification times, not a
fresh full-library checksum.

Later source-only metadata declaration corrections are covered by layout tests;
they do not add a handler and do not change the installed PB35 binary.
See [protocol investigation](docs/PB35-LEXUS-PROTOCOL.md).
