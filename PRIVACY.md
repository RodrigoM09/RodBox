# Public-export privacy boundary

This repository is a deliberately clean export. Original backup directories and the original private Git/configuration metadata were never used as the public repository's Git database.

Excluded: audio and audiobooks; downloaded cover/portrait art; library inventories and media filenames; tag databases and art caches; playlist/control/resume/bookmark/progress files; original config.cfg variants; device/volume identifiers; account names and host paths; original ELF/map/log/core/package backups; keychain data, tokens and unrelated HomeLab material. Generated binaries/debug bundles and Python caches inside source backups are excluded too.

Checkpoint records are newly written summaries. Source is selected from known upstream path lists and validated custom overlays. Necessary upstream build assets and upstream license/author information are retained. Upstream third-party contributor names are legitimate attribution and are not the device owner's private information.

A clean Git history uses neutral publication author/committer metadata. Every reachable commit, tag, path and blob is scanned for the private identifiers available to the exporter, host-path patterns and credential/private-key patterns before upload. The report records counts and categories rather than the private strings used in the checks. The working tree alone is not the boundary: historical blobs are scanned too.

The repository's hosting account is visible on GitHub because this is a public repository. That account namespace is separate from the files and neutral commit metadata. Source checkpoints do not restore personal settings or audiobook progress; those belong in a private offline backup.

Please apply the same redaction before posting Issues or PRs. An automated scan is one layer of review, not permission to upload arbitrary raw logs or backups.
