"""Actual Mikey decoder: captured remote3 replay and rapid-click regressions.

Uses extracted function bodies with register samples; no hardware is accessed.
The captured trace is reduced to anonymous tick/register values from the original
remote3 regression. This is not physical headset acceptance.
"""
from pathlib import Path
import os
import re
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
source = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "firmware-source/firmware/target/arm/s5l8702/ipod6g/mikey-6g.c"
s = source.read_text()
h = (root / "firmware-source/firmware/export/button.h").read_text()


def function(name):
    match = re.search(r"static (?:void|int|unsigned char) " + name + r"\([^;]*?\)\n\{", s)
    start = match.start()
    brace = s.index("{", start)
    depth, end = 1, brace + 1
    while depth:
        depth += (s[end] == "{") - (s[end] == "}")
        end += 1
    return s[start:end]


def structure(name):
    start = s.index("struct " + name + " {\n")
    return s[start:s.index("};", start) + 2]


code = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#define HZ 100
#define BUTTON_NONE 0
#define TIME_AFTER(a,b) ((long)((b)-(a)) < 0)
static long current_tick;
static bool track_skip;
'''
code += "\n".join(line for line in s.splitlines() if line.startswith("#define MIKEY_"))
code += "\n" + "\n".join(line for line in h.splitlines()
                         if re.match(r"#define BUTTON_MULTIMEDIA(?:\s|_(?:PLAYPAUSE|PREV|NEXT|VOLUME_UP|VOLUME_DOWN)\s)", line)) + "\n"
code += structure("mikey_local_decode") + structure("mikey_decode")
for name in ["mikey_local_decode_vol", "mikey_local_decode_reset", "mikey_local_vol_gate",
             "mikey_local_decode_poll", "mikey_decode_reset", "mikey_clicks_reset",
             "mikey_decode_poll"]:
    code += function(name)
code += r'''
static struct mikey_decode decoder;
static int seen_play, seen_next, seen_prev, seen_up, seen_down, previous;
static void poll(int reg4, int reg5) {
    current_tick += 2;
    int result=mikey_decode_poll(&decoder,reg4,reg5);
    if (result != previous && result) {
        seen_play += (result & BUTTON_MULTIMEDIA_PLAYPAUSE)==BUTTON_MULTIMEDIA_PLAYPAUSE;
        seen_next += (result & BUTTON_MULTIMEDIA_NEXT)==BUTTON_MULTIMEDIA_NEXT;
        seen_prev += (result & BUTTON_MULTIMEDIA_PREV)==BUTTON_MULTIMEDIA_PREV;
        seen_up += (result & BUTTON_MULTIMEDIA_VOLUME_UP)==BUTTON_MULTIMEDIA_VOLUME_UP;
        seen_down += (result & BUTTON_MULTIMEDIA_VOLUME_DOWN)==BUTTON_MULTIMEDIA_VOLUME_DOWN;
    }
    previous=result;
}
static void idle(int n) { while (n--) poll(0,0); }
static void setup(bool skip) {
    memset(&decoder,0,sizeof(decoder)); mikey_decode_reset(&decoder);
    mikey_clicks_reset(&decoder); track_skip=skip; current_tick=0;
    seen_play=seen_next=seen_prev=seen_up=seen_down=previous=0; idle(12);
}
static void taps(int count,int spacing) {
    for (int i=0;i<count;i++) { poll(0x05,0); idle(spacing-1); }
    idle(35);
}
struct sample { int tick; unsigned char btn,evt; };
/* Original remote3 host regression: insertion, volume-down, volume-up,
 * center press, and the trailing false volume report after its release. */
static const struct sample trace[]={
    {0,0x05,0},{15,0,0},{18,0x20,0x0c},{21,0x20,0},{24,0x20,0},
    {2636,0x24,0},{2651,0x24,0},{2657,0x20,0},{2660,0x20,1},{2663,0,0},{2666,0,0},
    {3435,4,0},{3450,4,0},{3459,4,0},{3462,0x20,0},{3465,0x20,0x0c},
    {3468,0x20,0},{3471,0x20,0},{4256,0x25,0},{4271,0x25,0},
    {4277,0x20,0},{4280,0,4},{4283,0,0},{4286,0,0}
};
static void captured_replay(void) {
    struct mikey_decode d={0}; mikey_decode_reset(&d); mikey_clicks_reset(&d);
    track_skip=false; int pos=0, prior=0, count=0, events[4];
    for (int tick=0;tick<4400;tick+=3) {
        while(pos+1<(int)(sizeof(trace)/sizeof(trace[0])) && trace[pos+1].tick<=tick) pos++;
        current_tick=tick; int result=mikey_decode_poll(&d,trace[pos].btn,trace[pos].evt);
        if(result && result!=prior) { assert(count<4); events[count++]=result; }
        prior=result;
    }
    assert(count==3); assert(events[0]==BUTTON_MULTIMEDIA_VOLUME_DOWN);
    assert(events[1]==BUTTON_MULTIMEDIA_VOLUME_UP);
    assert(events[2]==BUTTON_MULTIMEDIA_PLAYPAUSE);
}
int main(void) {
    captured_replay();
    setup(true); taps(1,10); assert(seen_play==1 && !seen_next && !seen_prev);
    setup(true); taps(2,10); assert(seen_next==1 && !seen_play && !seen_prev);
    setup(true); taps(3,10); assert(seen_prev==1 && !seen_play && !seen_next);
    /* Every accepted rise retains its six-poll classification slot. */
    for (int spacing=4;spacing<=12;spacing++) {
        setup(true); taps(2,spacing); assert(seen_next==1 && !seen_play && !seen_prev);
        setup(true); taps(3,spacing); assert(seen_prev==1 && !seen_play && !seen_next);
        setup(true); taps(4,spacing); assert(seen_prev==1 && !seen_play && !seen_next);
    }
    setup(false); taps(1,10); assert(seen_play==1 && !seen_next && !seen_prev);
    setup(false); poll(4,MIKEY_EVT_VOLUP_DN); idle(20);
    assert(seen_up==1 && !seen_play && !seen_down && previous==0);
    setup(true); poll(4,MIKEY_EVT_VOLDN_DN); idle(20);
    assert(seen_down==1 && !seen_play && !seen_up && previous==0);
    setup(false); poll(5,0); idle(1); poll(0,MIKEY_EVT_VOLDN_DN); idle(35);
    assert(seen_play==1 && !seen_down);
    /* No repeats from a stuck center, a lost volume release, or a short
     * center bounce. Reset/rearm drops every pending local classification. */
    setup(false); for(int i=0;i<500;i++) poll(5,0); idle(30);
    assert(seen_play==1 && previous==0);
    setup(false); poll(5,0); idle(2); poll(5,0); idle(30); assert(seen_play==1);
    setup(false); poll(5,0); idle(1); mikey_decode_reset(&decoder); idle(35);
    assert(!seen_play);
    for(int dir=0;dir<2;dir++) {
        setup(false); int press=dir?1:4;
        poll(4,press); for(int i=0;i<500;i++) poll(4,i<5?press:0);
        assert(!seen_play && previous==0 && (dir?seen_down:seen_up)==1);
    }
    /* All 65,536 sixteen-poll level sequences: with skip off there is one
     * bounded output per rise preceded by three released polls. With skip
     * on the same accepted rises choose exactly one single/double/triple. */
    for(unsigned mask=0;mask<65536;mask++) {
        int expected=0, low=3;
        for(int i=0;i<16;i++) {
            if(mask & (1u<<i)) { if(low>=3) expected++; low=0; }
            else if(low<3) low++;
        }
        for(int skip=0;skip<2;skip++) {
            setup(skip);
            for(int i=0;i<16;i++) poll((mask & (1u<<i))?5:0,0);
            idle(35);
            assert(!seen_up && !seen_down);
            if(!skip) assert(seen_play==expected && !seen_next && !seen_prev);
            else {
                assert(seen_play==(expected==1)); assert(seen_next==(expected==2));
                assert(seen_prev==(expected>=3));
            }
        }
    }
    puts("PASS: captured remote3 replay; 27 spaced-click cases; volume/hold/bounce/reset guards; 131072 exhaustive center sequences (ASan/UBSan)");
}
'''
with tempfile.TemporaryDirectory(prefix="mikey-audit-") as temp:
    harness = Path(temp) / "harness.c"
    executable = Path(temp) / "harness"
    harness.write_text(code)
    subprocess.run(["clang", "-std=c11", "-O1", "-g", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                    str(harness), "-o", str(executable)], check=True)
    subprocess.run([str(executable)], check=True,
                   env={**os.environ, "UBSAN_OPTIONS": "halt_on_error=1"})
