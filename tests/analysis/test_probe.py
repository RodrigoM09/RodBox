"""Exercise the actual PCM probe and fixed-point log with synthetic signals.

Hop/tempo/chroma services are controlled fixtures: these tests verify the probe's
accounting and lock lifetime, not the musical quality of the beat detector.
Build outputs live in a temporary directory, outside the source repository.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2] / 'firmware-source'

HARNESS = r'''
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "audio/beat_probe.h"
#include "audio/beat_track.h"
#include "dsp_core.h"
static struct beat_track mock_beat;
static unsigned fill, windows;
static struct beat_window window;
void beat_hops_reset(unsigned r) {(void)r;windows=0;}
void beat_hops_set_rate(unsigned r) {(void)r;}
void beat_hops_set_pos(unsigned long t) {(void)t;}
void beat_hops_feed(const int16_t *p,int n) {(void)p;(void)n;}
unsigned beat_hops_windows(void) {return windows;}
const struct beat_window *beat_hops_window(int back) {return back==0?&window:NULL;}
void beat_track_get(struct beat_track *b) {*b=mock_beat;}
unsigned beat_track_fill(void) {return fill;}
void chroma_reset(unsigned r) {(void)r;}
void chroma_feed(const int16_t *p,int n) {(void)p;(void)n;}
void chroma_get(struct chroma_result *r) {memset(r,0,sizeof(*r));}
static struct track_pcm fmt={48000,STEREO_NONINTERLEAVED,0};
static struct track_sound result;
static void block(int l,int r,int n,unsigned long t) {
 int32_t a[256],b[256];
 assert(n<=256);
 for(int i=0;i<n;i++){a[i]=l;b[i]=r;}
 beat_probe_sink(a,b,n,&fmt,t);
}
static void signal(int l,int r) {
 memset(&mock_beat,0,sizeof(mock_beat));fill=0;
 beat_probe_start();block(l,r,256,0);beat_probe_result(&result);
}
int main(void) {
 unsigned checks=0;
 for(int a=1;a<=16384;a*=2) {
   signal(a,a);int inphase=result.loudness_db10;
   double expected=200*log10((double)a/32768);
   assert(fabs(inphase-expected)<=2.0);checks++;
   assert(result.crest_db10<=2 && result.width==0);checks++;
   signal(a,-a);
   assert(result.loudness_db10==inphase && result.width==255);checks++;
 }
 signal(0,0);assert(result.loudness_db10==-960 && !result.crest_db10 && !result.width);checks++;
 signal(-32768,-32768);assert(result.loudness_db10==0 && !result.crest_db10);checks++;
 signal(20000,0);assert(result.width==255 && result.crest_db10>=29 && result.crest_db10<=32);checks++;
 signal(64,64);assert(result.loudness_db10>-960 && result.loudness_db10<-480);checks++;
 /* One block's duration exists even when all reported timestamps are zero. */
 beat_probe_start();fmt.frequency=48000;
 for(int i=0;i<375;i++)block(1000,1000,256,0);
 beat_probe_result(&result);assert(result.analysed_ms==2000);checks++;
 /* Mixed rates preserve elapsed samples without relabelling the earlier rate. */
 beat_probe_start();fmt.frequency=44100;
 for(int i=0;i<100;i++)block(1000,1000,147,0);
 fmt.frequency=48000;
 for(int i=0;i<100;i++)block(1000,1000,160,0);
 beat_probe_result(&result);assert(result.analysed_ms==666);checks++;
 /* Onsets/second use audio duration, not coarse codec timestamp differences. */
 beat_probe_start();fmt.frequency=48000;
 block(1000,1000,256,0);windows=1;window.onset=1;
 for(int i=1;i<375;i++)block(1000,1000,256,0);
 beat_probe_result(&result);assert(result.rate10[0]==5);checks++;
 /* Current lock, lost lock, octave change and re-settling. */
 beat_probe_start();fill=100;
 mock_beat=(struct beat_track){.locked=true,.period_ms=500,.confidence=70};
 block(1000,1000,256,0);block(1000,1000,256,3000);
 assert(beat_probe_settled());checks++;
 mock_beat.locked=false;block(1000,1000,256,3100);beat_probe_result(&result);
 assert(!result.settled && !result.period_ms && !result.confidence);checks++;
 mock_beat.locked=true;mock_beat.period_ms=1000;
 block(1000,1000,256,4000);assert(!beat_probe_settled());checks++;
 block(1000,1000,256,7000);assert(beat_probe_settled());checks++;
 mock_beat.period_ms=500;block(1000,1000,256,7100);
 assert(!beat_probe_settled());checks++;
 /* Mono and interleaved layouts use the same channel energy. */
 fmt.stereo_mode=STEREO_MONO;signal(4096,123);
 int mono=result.loudness_db10;
 fmt.stereo_mode=STEREO_INTERLEAVED;
 int32_t pcm[512];for(int i=0;i<512;i++)pcm[i]=4096;
 beat_probe_start();beat_probe_sink(pcm,NULL,256,&fmt,0);beat_probe_result(&result);
 assert(result.loudness_db10==mono);checks++;
 printf("PASS: %u probe checks; actual fixed-point log and PCM probe, ASan/UBSan\n",checks);
}
'''

with tempfile.TemporaryDirectory(prefix='rodbox-analysis-') as tmp:
    d = Path(tmp)
    (d/'config.h').write_text('/* host test: no hardware definitions */\n')
    (d/'dsp_core.h').write_text(
        'enum {STEREO_INTERLEAVED, STEREO_NONINTERLEAVED, STEREO_MONO};\n')
    (d/'probe.c').write_text(HARNESS)
    binary = d/'probe'
    subprocess.run(['clang', '-std=c11', '-O1', '-g', '-Wall', '-Wextra',
                    '-Werror', '-Wno-error=constant-conversion',
                    '-Wno-error=absolute-value', '-fsanitize=address,undefined',
                    '-fno-omit-frame-pointer', '-I'+str(d),
                    '-I'+str(ROOT/'apps-ipod'),
                    '-I'+str(ROOT/'lib/fixedpoint'), str(d/'probe.c'),
                    str(ROOT/'apps-ipod/audio/beat_probe.c'),
                    str(ROOT/'lib/fixedpoint/fixedpoint.c'), '-lm',
                    '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
