# Contributing and reusing parts

Take what is useful: individual patches, tests, companion utilities or the integration as a whole. Follow the relevant licenses and retain original attribution. Reusing a small piece does not require adopting the rest of RodBox.

Please open an Issue if you find a bug or have a useful improvement. Include the PB version or commit, hardware target, expected behavior, actual behavior and a short reproducible sequence. For artwork or library bugs, use synthetic filenames/tags where possible. Remove account names, local paths, device/volume serials, library inventories, listening history, credentials and media before attaching anything.

Pull requests are welcome. Keep one behavior change per PR; explain what it fixes and how it was checked. Preserve custom application behavior in `apps-ipod`; editing legacy `apps` alone does not change the active PodBox app layer. Preserve license headers and identify upstream inspiration or imported commits. Host tests are useful, but explicitly distinguish mocked tests from physical playback, storage and accessory checks.

AI-assisted contributions are welcome when reviewed and tested. Say where AI helped, what you checked and what remains unverified. Do not claim AI generated upstream work or that a successful build proves hardware safety, audio quality or battery savings.

Never include personal device backups or copyrighted media in a contribution. Treat format/partition/bootloader changes as separate work; they are not routine firmware updates here.
