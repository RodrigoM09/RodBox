"""Actual scan measurement body stops on persistence errors without counting success."""
from pathlib import Path
import importlib.util
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('extractor', ROOT/'tests/storage/test_usb_idle.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
actual = module.extract((ROOT/'firmware-source/apps-ipod/screens/system/sound_scan.c').read_text(), 'ss_measure')
HARNESS = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "database/sound_index.h"
#define SS_START_PCT 20
#define SS_START_MIN_MS 5000
#define SS_START_MAX_MS 60000
#define SS_WINDOW_MS 40000
#define SS_WINDOW_BYTES 4096
#define SS_MIN_LENGTH_MS 25000
#define ANALYSIS_QUICK 0
static struct {int analysis_depth;} global_settings;
static bool ss_stop,ss_unplugged,ss_write_failed,already_done,add_ok;
static int ss_skipped,ss_failed,ss_done,decode_rc,adds;
static long current_tick,ss_work;
static unsigned long ss_audio_ms;
static uint64_t path_key(const char *p){(void)p;return 123;}
static uint32_t ss_file_size(const char *p){(void)p;return 1000;}
bool sound_index_done(uint64_t key,uint32_t mtime,uint32_t size){(void)key;(void)mtime;(void)size;return already_done;}
bool sound_index_add(const struct sound_record *r){(void)r;adds++;return add_ok;}
void sound_index_fill(struct sound_record *r,uint64_t k,uint32_t m,uint32_t z,uint32_t g,int y,const struct track_sound *s,int rc){
 (void)k;(void)m;(void)z;(void)g;(void)y;(void)s;(void)rc;memset(r,0,sizeof(*r));
}
void beat_probe_start(void){}
void beat_probe_result(struct track_sound *s){memset(s,0,sizeof(*s));}
static int fake_decode(unsigned long *n){*n=40000;return decode_rc;}
#define track_decode_run(path,start,window,buffer,bytes,sink,enough,abort,ms) \
 ((void)(path),(void)(start),(void)(window),(void)(buffer),(void)(bytes),fake_decode(ms))
/* ACTUAL */
int main(void){
 global_settings.analysis_depth=1;
 for(int rc=TRACK_DECODE_FAILED;rc<=TRACK_DECODE_OK;rc++){
  decode_rc=rc;add_ok=false;ss_write_failed=false;ss_done=ss_failed=ss_skipped=adds=0;ss_audio_ms=0;
  assert(!ss_measure("track",1,2,2000,120000,NULL));
  assert(ss_write_failed && adds==1 && ss_done==0 && ss_failed==0 && ss_audio_ms==0);
  add_ok=true;ss_write_failed=false;
  assert(ss_measure("track",1,2,2000,120000,NULL));
  assert(!ss_write_failed && ss_done==1 && ss_failed==(rc!=TRACK_DECODE_OK) && ss_audio_ms==40000);
 }
 already_done=true;adds=0;assert(ss_measure("track",1,2,2000,120000,NULL));assert(adds==0 && ss_skipped==1);
 already_done=false;decode_rc=TRACK_DECODE_NO_THREAD;assert(ss_measure("track",1,2,2000,120000,NULL));assert(adds==0 && ss_skipped==2);
 puts("PASS: save failure ends measurement and does not count progress; cache/no-thread skips retained; ASan/UBSan");
}
'''
with tempfile.TemporaryDirectory(prefix='rodbox-scan-') as tmp:
    d = Path(tmp)
    (d/'test.c').write_text(HARNESS.replace('/* ACTUAL */', actual))
    subprocess.run(['clang', '-std=c11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', '-I'+str(ROOT/'firmware-source/apps-ipod'),
                    str(d/'test.c'), '-o', str(d/'test')], check=True)
    subprocess.run([str(d/'test')], cwd=d, check=True)
