"""Run the actual Classic ATA policy and transfer bodies with mocked hardware.

This checks event ordering, mutex-boundary races and error control flow, not USB
electrical behavior or flash reliability. The native target build remains needed.
Tick arithmetic uses the firmware's configured signed-wrap compiler semantics.
"""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'firmware-source/firmware/target/arm/s5l8702/ipod6g/storage_ata-6g.c'


def extract(source, name):
    """Copy a complete definition verbatim, ignoring braces in comments/strings."""
    match = re.search(r'^(?:static )?(?:void|bool|int) ' + name +
                      r'\([^;]*?\)\s*\{', source, re.M)
    if match is None:
        raise ValueError(f'Missing actual function: {name}')
    depth = 1
    tokens = re.finditer(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|'
                         r"'(?:\\.|[^'\\])*'|[{}]",
                         source[match.end():], re.S)
    for token in tokens:
        if token.group() == '{':
            depth += 1
        elif token.group() == '}':
            depth -= 1
            if depth == 0:
                return source[match.start():match.end() + token.end()]
    raise ValueError(f'Unclosed actual function: {name}')


def main():
    source = SOURCE.read_text()
    functions = '\n\n'.join(extract(source, name) for name in (
        'ata_set_active', 'ata_soft_reset', 'ata_hard_reset', 'ata_reset', 'ata_transfer_sectors', 'ata_read_sectors', 'ata_write_sectors',
        'ata_sleepnow_locked', 'ata_sleepnow', 'ata_event'))
    template = Path(__file__).with_name('usb_idle_harness.c').read_text()
    # Exercise the actual packed error representation with full UBSan.
    header = SOURCE.with_name('mmcdefs-target.h').read_text()
    macros = header[header.index('#define ERR_RC('):header.index('#define TIMEOUT_EXPIRED')]
    system = (ROOT / 'firmware-source/firmware/export/system.h').read_text()
    timing = '\n'.join(re.findall(r'^#define TIME_(?:AFTER|BEFORE)\([^\n]*', system, re.M))
    assert timing.count('#define') == 2
    unit = template.replace('/* ACTUAL_TIME_MACROS */', timing).replace(
        '/* ACTUAL_ERROR_MACROS */', macros).replace(
        '/* ACTUAL_FUNCTIONS */', functions)
    with tempfile.TemporaryDirectory(prefix='rodbox-usb-idle-') as tmp:
        path = Path(tmp)
        (path / 'idle.c').write_text(unit)
        # BOOTLOADER and sector configuration exercise the same extracted code
        # under the relevant preprocessor choices; not a whole firmware build.
        for defines in ([], ['-DBOOTLOADER'], ['-DHAVE_ATA_DMA'],
                        ['-DBOOTLOADER', '-DHAVE_ATA_DMA']):
            print('Configuration: ' + (' '.join(defines) or 'normal'), flush=True)
            subprocess.run(['clang', '-std=gnu11', '-O1', '-g', '-Wall',
                            '-Wextra', '-Werror', '-fsanitize=address,undefined',
                            '-fno-strict-overflow',
                            # The real write wrapper casts through the target's
                            # 32-bit pointer width. No host dereference uses it.
                            '-Wno-pointer-to-int-cast', '-Wno-int-to-pointer-cast',
                            *defines,
                            str(path / 'idle.c'), '-o', str(path / 'idle')], check=True)
            subprocess.run([str(path / 'idle')], check=True)


if __name__ == '__main__':
    main()
