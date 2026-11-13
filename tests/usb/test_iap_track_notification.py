from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[2]
s=(r/'firmware-source/firmware/usbstack/iap/notification.c').read_text()
a=s.index('void iap_on_track_playback_index(');b=s.index('void iap_on_tracks_count(',a)
pre=r"""
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
struct IAPContext {int unused;};static struct IAPContext ctx;
static bool iap_initialized;static unsigned calls,last;
static struct IAPContext *_iap_acquire_ctx(bool b){assert(!b);return &ctx;}
static void iap_notify_track_playback_index(struct IAPContext*c,uint32_t n){assert(c==&ctx);calls++;last=n;}
"""
main=r"""
int main(void){
 iap_on_track_playback_index(4,false);assert(!calls);
 iap_initialized=true;
 iap_on_track_playback_index(4,false);assert(calls==1&&last==4);
 iap_on_track_playback_index(5,true);assert(calls==2&&last==5);
 puts("PASS: track notifications independent of artwork/PCM readiness; disconnected guard retained");
}
"""
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(pre+s[a:b]+main)
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True)
 subprocess.run([str(p/'t')],check=True)
