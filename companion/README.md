# Companion utilities

These helpers were independently implemented with design inspiration from HifiMule and rockbox-library-manager; see CREDITS.md. They operate only on explicitly supplied paths/manifests. They do not format, scan-and-delete, retag or reorganize a music library automatically.

`verified_copy.py` provides contained staged copy, source-change checking, SHA256, sync, atomic replacement, existing-destination safeguards and resume/idempotence. Its API requires explicit expected size/hash and an explicit old hash before replacement. Volume identity/cancellation checks can be supplied by the caller. Test files use synthetic content.

`health_report.py` rejects disconnected, failed or incomplete inventories. It reports missing tags/artwork, spelling variants and exact backup gaps; it does not repair media or delete entries. A failed scan preserves the prior completed report.

Run `python3 -m unittest discover -s companion -p 'test_*.py'` from the repository root. Source and tests are GPL-2.0-or-later. Do not include private inventory/report JSON in a public issue.
