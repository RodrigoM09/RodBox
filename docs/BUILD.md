# Building the PodBox-based checkpoints

The current pinned foundation is anthonyfletcher/podbox at `0fe9c63355c4fc63e892237d019666fff4932a13`. The active application directory is **apps-ipod**, not legacy apps.

The recorded native compiler was Arm GNU Toolchain **13.2.Rel1**, using `arm-none-eabi-gcc`. Install a compatible toolchain separately; its binaries are not vendored here. Put its bin directory on PATH. Build outside the source directory:

```sh
mkdir build
cd build
../firmware-source/tools/configure --appsdir=apps-ipod --compiler-prefix=arm-none-eabi- --target=ipod6g --ram=64 --rbdir=/.rockbox --type=N
make -j4
```

This produces the firmware core and build information; a deliberately packaged deployment must also include the matching codecs, fonts, native Scrim/theme data and any required help/data files. Use the pinned upstream build/bundle documentation for a complete package. No personal-device configuration is supplied or installed automatically.

The recorded image header is `ip6g`; the target checksum is the payload-byte sum plus target model value 71. A successful target build and checksum do not establish that every accessory/storage combination works.

Check out `checkpoint/pbN` to inspect a historical version. PB1–PB3 are reconstructed from retained artifacts and have not all been independently rebuilt as published. Earlier legacy checkpoints use Rockbox's old apps layer and must not use the apps-ipod build argument; consult their checkpoint notes. Evidence-only tags may not contain a complete firmware source tree.

Original firmware binaries are intentionally absent because they can embed absolute host paths and are not complete clean redistributable packages. Build the source in your own environment and perform the checks in TESTING.md.

Portable test scripts and companion tools were added in the final publication commits. Historical source tags may predate those files; use the latest test scripts against a separate checkout of the chosen source tag.

For the PB27 core and 40 matching codecs, use the configuration above and run `make -j4 VERSION=rodbox-pb27-dbunique-261029 bin codecs`. Keep the matching existing target assets. This builds an experimental candidate, not a recovery image or proof of storage reliability.
