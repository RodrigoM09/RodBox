"""Actual power-input update helper: wake on connection, not charging pulses."""
from pathlib import Path
import subprocess,tempfile

root=Path(__file__).resolve().parents[2]
s=(root/'firmware-source/firmware/powermgmt.c').read_text()
a=s.index('static void power_thread_update_inputs(')
b=s.index('\n#endif\n\nstatic void power_thread(void)',a)
helper=s[a:b]
pre='''#include <assert.h>
#include <stdio.h>
#define HAVE_BACKLIGHT
#define POWER_INPUT 0x0f
static unsigned power_thread_inputs;
static unsigned wakes,expected;
static void backlight_on(void){assert(power_thread_inputs==expected);wakes++;}
'''
tests='''
static void step(unsigned value,unsigned count){expected=value;power_thread_update_inputs(value);assert(wakes==count);}
int main(void){
 step(0,0);step(2,1);step(2,1);step(0x22,1);step(2,1);
 step(0x102,1);step(0x100,1);step(1,2);step(0x11,2);
 step(2,2);step(0,2);step(0,2);step(2,3);step(0,3);step(1,4);
 puts("PASS: 15 USB/main input, full-battery, charging-flag, removal/reconnect and cache-before-wake cases; ASan/UBSan");
}
'''
with tempfile.TemporaryDirectory(prefix='rodbox-plug-wake-') as tmp:
 p=Path(tmp);(p/'wake.c').write_text(pre+helper+tests)
 subprocess.run(['clang','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'wake.c'),'-o',str(p/'wake')],check=True)
 subprocess.run([str(p/'wake')],check=True)
