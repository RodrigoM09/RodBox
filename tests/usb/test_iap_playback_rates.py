"""Exercise production wait/negotiation bodies with deterministic state."""
from pathlib import Path
import subprocess, tempfile
root = Path(__file__).resolve().parents[2]
src = root/'firmware-source/firmware/usbstack/iap'
def body(file, start, end):
    text=(src/file).read_text()
    return text[text.index(start):text.index(end,text.index(start))]
code=r"""
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#define AUDIO_STATUS_PLAY 1
#define AUDIO_STATUS_PAUSE 2
#define HZ 100
#define TIME_AFTER(a,b) ((long)((b)-(a))<0)
#define check_act(c,a,...) do {if(!(c)){a;}}while(0)
#define ARRAYLEN(a) (sizeof(a)/sizeof((a)[0]))
#define USB_LOG_IAP_RATES 0
#define usb_log(...) ((void)0)
struct Platform {bool control_pending, pending_wants_play; int pending_control; long pending_tick;};
struct IAPContext {struct Platform *platform;};
static bool library_play_held, building, response;
static int status, replies;
static long current_tick;
static int audio_status(void){return status;}
static bool iap_library_building(void){return building;}
static bool iap_control_response(struct IAPContext*c,int p,bool ok){(void)c;(void)p;replies++;response=ok;return true;}
struct IAPSpan {const unsigned char *data; size_t size;};
static int reads;
static bool iap_span_read_32(struct IAPSpan*s,uint32_t*v){
 reads++; assert(s->size>=4);*v=(uint32_t)s->data[0]<<24|(uint32_t)s->data[1]<<16|(uint32_t)s->data[2]<<8|s->data[3];s->size-=4;s->data+=4;return true;
}
static const unsigned long samprs[]={48000,44100,32000};
static unsigned offered;
static void offer_rates(unsigned mask){offered=mask;}
"""
code+=body('platform.c','bool iap_platform_control_waits','void iap_platform_control(')
code+=body('audio.c','bool iap_audio_accessory_rates','void iap_audio_take_counts')
code+=r"""
int main(void){
 struct Platform p={.control_pending=true,.pending_wants_play=true};
 struct IAPContext c={&p};
 status=3;assert(iap_platform_control_waits(&c));assert(!replies);
 status=1;assert(!iap_platform_control_waits(&c));assert(response&&replies==1);
 p.control_pending=true;p.pending_wants_play=false;
 assert(iap_platform_control_waits(&c));status=3;
 assert(!iap_platform_control_waits(&c));assert(response&&replies==2);
 p.control_pending=true;p.pending_wants_play=true;current_tick=501;
 assert(!iap_platform_control_waits(&c));assert(!response&&replies==3);
 p.control_pending=true;library_play_held=true;building=true;
 assert(iap_platform_control_waits(&c));assert(replies==3);
 building=false;status=1;
 assert(!iap_platform_control_waits(&c));assert(response&&replies==4);
 unsigned char rates[]={0,0,0xbb,0x80,0,0,0xac,0x44,0,0,0x7d,0};
 struct IAPSpan s={rates,12};assert(iap_audio_accessory_rates(&s));assert(reads==3&&offered==7);
 for(size_t n=0;n<12;n++)if(!n||n%4){s=(struct IAPSpan){rates,n};reads=0;assert(!iap_audio_accessory_rates(&s));assert(reads==0);}
 unsigned char bad[]={0,0,0,1};s=(struct IAPSpan){bad,4};offered=0;
 assert(!iap_audio_accessory_rates(&s));assert(!offered);
 puts("PASS: paused/resumed/timeout/library acknowledgements; valid, empty, truncated and unsupported rate lists");
}
"""
with tempfile.TemporaryDirectory() as d:
    p=Path(d);(p/'t.c').write_text(code)
    subprocess.run(['clang','-Wall','-Wextra','-Werror','-Wno-unused-but-set-variable','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True)
    subprocess.run([str(p/'t')],check=True)
