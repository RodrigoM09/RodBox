"""Production resampler vectors; host ASan/UBSan, no Python DSP simulation.

Run with /usr/bin/python3 tests/audio/test_resample_bandlimit.py.
--require-bandlimit turns the alias measurements into acceptance assertions.
--evidence DIR preserves measurements and build/run logs outside scratch.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
DSP = ROOT / 'firmware-source/lib/rbcodec/dsp'

def build(work):
    (work / 'rbcodecconfig.h').write_text('''#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#define IBSS_ATTR
#define INIT_ATTR
#define DSP_OUT_DEFAULT_HZ 44100
#define MIN(a,b) ((a)<(b)?(a):(b))
''')
    (work / 'platform.h').write_text('/* host platform only */\n')
    binary = work / 'resample-current'
    command = ['clang', '-std=gnu99', '-O2', '-g', '-Wall', '-Wextra',
               '-Werror', '-fsanitize=address,undefined',
               '-fno-sanitize-recover=all',
               '-I'+str(work), '-I'+str(DSP),
               '-I'+str(ROOT/'firmware-source/apps-ipod/system'),
               '-idirafter', str(ROOT/'firmware-source/firmware/include'),
               '-I'+str(ROOT/'firmware-source/lib/fixedpoint'),
               str(ROOT/'tests/audio/resample_vectors.c'), '-o', str(binary)]
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stdout+result.stderr)
    return binary

def execute(binary, *args):
    result = subprocess.run([str(binary), *map(str,args)], text=True,
                            capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stdout+result.stderr)
    return result.stdout.strip()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-bandlimit', action='store_true')
    parser.add_argument('--evidence', type=Path)
    args = parser.parse_args()
    measurements = []
    with tempfile.TemporaryDirectory(prefix='pb56-resample-') as d:
        work = Path(d)
        binary = build(work)
        print(execute(binary, 'selftest'), flush=True)
        for fin, fout, tones in [
            (96000,48000,[1000,10000,18000,20000,24000,26000,30000,40000]),
            (88200,44100,[1000,10000,18000,20000,22050,24000,30000]),
            (48000,44100,[1000,10000,18000,20000,22050,22500,23000]),
        ]:
            for hz in tones:
                db = float(execute(binary, 'tone', fin, fout, hz, 509))
                row = dict(implementation="current-unmodified", fin=fin, fout=fout,
                           tone_hz=hz, output_rms_db_relative_input=db)
                measurements.append(row)
                print(json.dumps(row), flush=True)
    if args.evidence:
        args.evidence.mkdir(parents=True, exist_ok=True)
        (args.evidence/'resample-measurements.json').write_text(
            json.dumps(measurements, indent=2)+'\n')
    if args.require_bandlimit:
        failures = [r for r in measurements if r['tone_hz'] > r['fout']/2
                    and r['output_rms_db_relative_input'] > -40]
        assert not failures, f'Alias rejection below 40 dB: {failures}'
    print('PASS: characterized unchanged production C resampler under ASan/UBSan; anti-alias improvement DEFERRED, not fixed')

if __name__ == '__main__':
    main()
