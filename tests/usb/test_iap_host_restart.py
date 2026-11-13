"""Real SET_CUR rate handler: late host command recovers only enabled streams."""
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[2]
s=(r/'firmware-source/firmware/usbstack/iap/audio.c').read_text();a=s.index('bool iap_audio_set_sampr(');b=s.index('\n}',a)+2
pre=r'''
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#define USB_BATCH_NON_NATIVE
#define ARRAYLEN(a) (sizeof(a)/sizeof((a)[0]))
#define RATE(f) samprs[f]
#define usb_log(...) ((void)0)
#define LOG(...) ((void)0)
#define ERROR(...) ((void)0)
#define check_act(c,a,...) do{if(!(c)){a;}}while(0)
static const unsigned long samprs[]={48000,44100,32000};
static struct {struct {unsigned num_samprs;}caps;} iap_pcm_sink={{3}};
static bool accessory_ready=true,host_set_rate,enabled=true;
static int host_rate,host_rate_tick,host_rate_set_tick,current_tick,set_freq=1,cur_freq=-1;
static unsigned starts;
static bool start_ok=true;
static bool iap_audio_enable(void){starts++;return start_ok;}
'''
main=r'''
int main(void){
 assert(iap_audio_set_sampr(44100)&&starts==1&&cur_freq==1&&host_set_rate);
 enabled=false;assert(iap_audio_set_sampr(44100)&&starts==1);
 enabled=true;assert(iap_audio_set_sampr(48000)&&starts==1); /* stale mismatch */
 assert(!iap_audio_set_sampr(12345)&&starts==1);
 start_ok=false;assert(!iap_audio_set_sampr(44100)&&starts==2);
 puts("PASS: late matching SET_CUR restarts enabled stream; alt-off, invalid/stale rates excluded; restart failure returned");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(pre+s[a:b]+main)
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True)
 subprocess.run([str(p/'t')],check=True)
