"""Compatibility entry point for the flush-error regression test.

The original diagnostic reproduced PB19's false success. The maintained test
now checks that current production code propagates all injected failures.
An optional source argument permits verification against an older driver.
"""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('test_flush_errors.py')), run_name='__main__')
