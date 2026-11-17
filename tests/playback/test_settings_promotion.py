"""Actual startup settings promotion with injected filesystem failures."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
source = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "firmware-source/apps-ipod/settings/settings.c"
s = source.read_text()
start = s.index("static void rename_temp_file(")
end = s.index("\n#endif", start)
function = s[start:end]
code = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
static int current, temp, old, calls, fail_mask;
static int *file_at(const char *name) {
    if(!strcmp(name,"current")) return &current;
    if(!strcmp(name,"new")) return &temp;
    if(!strcmp(name,"old")) return &old;
    assert(0); return NULL;
}
static bool file_exists(const char *name) { return *file_at(name)!=0; }
static int mock_rename(const char *src,const char *dst) {
    calls++;
    if(fail_mask & (1<<calls)) return -1;
    int *from=file_at(src), *to=file_at(dst);
    if(!*from) return -1;
    *to=*from; *from=0; return 0;
}
#define rename mock_rename
'''+function+r'''
static void setup(void) { current=1; temp=2; old=3; calls=fail_mask=0; }
int main(void) {
    setup(); temp=0; rename_temp_file("new","current","old");
    assert(current==1 && old==3 && calls==0);
    setup(); current=0; rename_temp_file("new","current","old");
    assert(current==2 && !temp && old==3 && calls==1);
    setup(); rename_temp_file("new","current","old");
    assert(current==2 && !temp && old==1 && calls==2);
    setup(); fail_mask=1<<2; rename_temp_file("new","current","old");
    assert(current==1 && temp==2 && !old && calls==3);
    setup(); fail_mask=1<<1; rename_temp_file("new","current","old");
    assert(current==1 && temp==2 && old==3 && calls==1);
    setup(); rename_temp_file("new","current",NULL);
    assert(current==2 && !temp && old==3 && calls==1);
    setup(); fail_mask=1<<1; rename_temp_file("new","current",NULL);
    assert(current==1 && temp==2 && old==3 && calls==1);
    setup(); fail_mask=(1<<2)|(1<<3); rename_temp_file("new","current","old");
    assert(!current && temp==2 && old==1 && calls==3);
    puts("PASS: 8 startup settings/resume promotion cases; failed promotion restores prior file when rollback succeeds");
}
'''
with tempfile.TemporaryDirectory(prefix="settings-promotion-audit-") as temp:
    harness = Path(temp) / "harness.c"
    executable = Path(temp) / "harness"
    harness.write_text(code)
    subprocess.run(["clang", "-std=c11", "-O1", "-g", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                    str(harness), "-o", str(executable)], check=True)
    subprocess.run([str(executable)], check=True,
                   env={**os.environ, "UBSAN_OPTIONS": "halt_on_error=1"})
