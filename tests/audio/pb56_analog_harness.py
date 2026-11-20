"""PB56 analog host harness utilities; no device access.

Production function bodies and headers are copied verbatim except #includes
and #pragma once (headers are assembled into a single translation unit).
Only hardware, scheduling and unavailable dependencies are stubbed by callers.
"""
from pathlib import Path
import os
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'firmware-source'


def text(path):
    return (SRC / path).read_text()


def no_includes(source):
    return re.sub(r'^\s*#(?:include[^\n]*|pragma once)', '', source, flags=re.M)


def function(source, name):
    match = re.search(r'^[^\n;{}]*\b' + re.escape(name) + r'\([^;]*?\)\n\{', source, re.M)
    if not match:
        raise ValueError('Production function not found: ' + name)
    start = match.start()
    brace = source.index('{', start)
    depth, end = 1, brace + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end] + '\n'


def run_c(code, args=(), defines=()):
    # The invoking build supplies TMPDIR; remain portable outside Hermes.
    scratch = Path(os.environ.get('TMPDIR', tempfile.gettempdir()))
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='pb56-analog-', dir=scratch) as directory:
        source = Path(directory) / 'harness.c'
        binary = Path(directory) / 'harness'
        source.write_text(code)
        command = ['clang', '-std=gnu11', '-g', '-O1', '-Wall', '-Wextra',
                   '-Werror=implicit-function-declaration', '-Wno-unused-function',
                   '-Wno-unused-parameter', '-fsanitize=address,undefined',
                   '-fno-sanitize-recover=all', '-fno-omit-frame-pointer',
                   *['-D' + d for d in defines], str(source), '-o', str(binary)]
        built = subprocess.run(command, text=True, capture_output=True)
        if built.returncode:
            raise AssertionError('C compile failed:\n' + built.stdout + built.stderr)
        if built.stderr:
            print(built.stderr, end='')
        env = dict(os.environ, ASAN_OPTIONS='detect_leaks=0',
                   UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1', TMPDIR=str(scratch))
        return subprocess.run([str(binary), *args], text=True, capture_output=True, env=env)


COMMON = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#define MAX(a,b) ((a)>(b)?(a):(b))
#define MIN(a,b) ((a)<(b)?(a):(b))
#define ARRAYLEN(a) (sizeof(a)/sizeof((a)[0]))
#define LIKELY(x) (x)
#define UNLIKELY(x) (x)
#define FORCE_INLINE inline
#define SHAREDBSS_ATTR
#define IBSS_ATTR
#define INIT_ATTR
#define MEM_ALIGN_ATTR __attribute__((aligned(4)))
#define HZ 100
#define logf(...) ((void)0)
'''
