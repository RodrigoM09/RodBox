# Contributing and reusing parts

## Branch workflow

- `main` is the stable reference branch and is locked read-only, including for administrators. Force pushes and deletion are disabled. The owner must deliberately unlock it before promoting a reviewed, tested contribution.
- `community` is the working contribution branch. Collaborators with write access may push ordinary commits there; others should fork the repository and open a pull request **targeting `community`**.
- Anyone can clone, pull or fork this public repository. GitHub does not allow anonymous public pushes; direct push access requires an invitation from the owner. Request collaborator access through an Issue if ongoing work needs it.
- Do not put credentials, private device files or media into either branch. Keep changes focused and report the checks performed.


Take what is useful: individual patches, tests, companion utilities or the integration as a whole. Follow the relevant licenses and retain original attribution. Reusing a small piece does not require adopting the rest of RodBox.

Please open an Issue if you find a bug or have a useful improvement. Include the PB version or commit, hardware target, expected behavior, actual behavior and a short reproducible sequence. For artwork or library bugs, use synthetic filenames/tags where possible. Remove account names, local paths, device/volume serials, library inventories, listening history, credentials and media before attaching anything.

Pull requests are welcome. Keep one behavior change per PR; explain what it fixes and how it was checked. Preserve custom application behavior in `apps-ipod`; editing legacy `apps` alone does not change the active PodBox app layer. Preserve license headers and identify upstream inspiration or imported commits. Host tests are useful, but explicitly distinguish mocked tests from physical playback, storage and accessory checks.

AI-assisted contributions are welcome when reviewed and tested. Say where AI helped, what you checked and what remains unverified. Do not claim AI generated upstream work or that a successful build proves hardware safety, audio quality or battery savings.

Never include personal device backups or copyrighted media in a contribution. Treat format/partition/bootloader changes as separate work; they are not routine firmware updates here.
