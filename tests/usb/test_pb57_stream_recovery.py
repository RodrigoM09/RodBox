"""PB57: a USB iAP stream stopped by one failed packet is restarted.

Compiles the production non-native batch pump (usb_core.c) together with the
production iAP sink recovery (iap/audio.c) under ASan/UBSan and drives them
with a simulated host that keeps the streaming interface enabled. Before PB57
a single failed or short isochronous completion (for example a missed
interval while the player was busy waking its screen after the hold switch)
stopped the pump until the host sent SET_CUR/SET_INTERFACE again, which a
car that keeps polling never does: silence until the cable was pulled.

Usage: test_pb57_stream_recovery.py [source-root]
A source root without the PB57 recovery reproduces the permanent silence and
fails (RED); the current tree passes (GREEN).
"""
from pathlib import Path
import subprocess, sys, tempfile

repo = Path(__file__).resolve().parents[2]
root = Path(sys.argv[1]) if len(sys.argv) > 1 else repo / 'firmware-source'
core = (root / 'firmware/usbstack/usb_core.c').read_text()
audio = (root / 'firmware/usbstack/iap/audio.c').read_text()
iap = (root / 'firmware/usbstack/usb_iap.c').read_text()

a = core.index('static uint8_t batch_ep = 0;')
pump = core[a:core.index('\n#endif', a)]

marker = '#ifdef USB_BATCH_NON_NATIVE\n/* The USB interrupt stops the stream'
if marker in audio:
    a = audio.index(marker) + len('#ifdef USB_BATCH_NON_NATIVE\n')
    recover = audio[a:audio.index('#else\nvoid iap_audio_recover_stream', a)]
else:
    # PB56 and earlier: nothing restarts a stopped stream from the thread.
    recover = 'void iap_audio_recover_stream(void){(void)usb_log;}\n'
if 'bool usb_drv_batch_faulted(void)' not in pump:
    pump += '\nbool usb_drv_batch_faulted(void){return false;}\n'

# The tick must reach the recovery ahead of its early returns.
tick = iap[iap.index('static void usb_iap_notify_event('):]
order_ok = ('iap_audio_recover_stream();' in tick and
            tick.index('iap_audio_recover_stream();') <
            tick.index('if(iap_platform_control_waits(ctx))'))

pre = r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#define logf(...) ((void)0)
#define EP_NUM(n) ((n)&15)
#define HZ 100
#define TIME_AFTER(a,b) ((long)((b)-(a))<0)
#define TIME_BEFORE(a,b) TIME_AFTER(b,a)
#define USB_LOG_IAP2_EVENT 1
#define USB_LOG_IAP_STREAM_RESTART 19
typedef void(*usb_drv_batch_get_more)(const void**,size_t*);
int usb_drv_batch_stop(void);
static long current_tick;
static bool enabled;                 /* the host's alternate 1, audio.c */
static unsigned pulls, sends, resets, logged[256], nlogged, failed_logs;
static bool hw_busy;
static size_t source_length = 192;
static uint8_t pcm[192];
static void source(const void**p,size_t*n){pulls++;*p=pcm;*n=source_length;}
static int usb_drv_send_nonblocking(int ep,void*p,size_t n){
    assert(ep==1&&p==pcm&&n==source_length);assert(!hw_busy);
    sends++;hw_busy=true;return 0;}
static int disable_irq_save(void){return 0;}
static void restore_irq(int n){(void)n;}
static void usb_drv_reset_endpoint(int ep,bool send);
static void usb_log(int t,int a,int b,unsigned c,unsigned d){
    assert(t==USB_LOG_IAP2_EVENT&&a==USB_LOG_IAP_STREAM_RESTART&&b==0);
    if(nlogged<256)logged[nlogged++]=c; if(d)failed_logs++;}
'''

main = r'''
static void usb_drv_reset_endpoint(int ep,bool send){assert(ep==1&&send);hw_busy=false;resets++;}
/* The controller finishing the queued packet: ok, or a missed interval. */
static void complete(bool ok){
    if(!hw_busy)return;
    hw_busy=false;
    batch_xfer_complete(ok?0:-1, ok?(int)source_length:0);
}
/* The USB thread's 100 ms tick */
static void tick(void){current_tick+=HZ/10;iap_audio_recover_stream();}
static void enable(void){enabled=true;assert(!usb_drv_batch_start());}
static void disable(void){assert(!usb_drv_batch_stop());enabled=false;}

int main(void){
    assert(!usb_drv_batch_init(0x81,source));
    enable();
    for(int i=0;i<100;i++)complete(true);
    assert(pulls==101&&!batch_stopped&&!usb_drv_batch_faulted());

    /* One missed interval: the IRQ stops and never retries itself. */
    complete(false);
    assert(batch_stopped&&pulls==101);
    tick();
    if(batch_stopped){
        for(int i=0;i<600;i++)tick();       /* a minute of silence */
        printf("RED: one failed packet left the enabled stream stopped for a "
               "simulated minute (%u packets pulled, %u restarts)\n",pulls-101,resets-1);
        return 1;
    }
    assert(!usb_drv_batch_faulted()&&pulls==102&&nlogged==1&&logged[0]==1);
    for(int i=0;i<1000;i++)complete(true);   /* audio flows again */
    assert(pulls==1102&&!batch_stopped);

    /* After two healthy seconds the next fault is a first attempt again. */
    for(int i=0;i<25;i++)tick();
    complete(false);tick();
    assert(!batch_stopped&&nlogged==2&&logged[1]==1);
    complete(true);

    /* A host that has really stopped reading: every packet fails. Restarts
     * back off (3 immediate, then 1/s, then 1/10 s) so PCM is not drained. */
    unsigned before=pulls, restarts_before=resets;
    complete(false);
    assert(batch_stopped&&usb_drv_batch_faulted());
    for(int i=0;i<1200;i++){tick();complete(false);}    /* 120 s */
    unsigned restarts=resets-restarts_before;
    assert(restarts>=60&&restarts<=70);
    assert(pulls-before==restarts);        /* one packet of PCM per restart */
    /* logs: attempts 1,2,3 then powers of two only */
    for(unsigned i=2;i<nlogged;i++){unsigned n=logged[i];assert(n<=3||!(n&(n-1)));}
    assert(failed_logs==0);

    /* The host disables the interface: no restarts, no fault left behind. */
    disable();
    assert(!usb_drv_batch_faulted());
    unsigned r=resets;
    for(int i=0;i<100;i++)tick();
    assert(resets==r);

    /* Re-enabled by the host: a normal start, recovery idle while healthy. */
    enable();complete(true);
    for(int i=0;i<100;i++){tick();complete(true);}
    assert(!batch_stopped&&!usb_drv_batch_faulted());

    /* An explicit stop or an exhausted source is not a fault. */
    disable();enabled=true;
    for(int i=0;i<20;i++)tick();
    assert(batch_stopped&&!usb_drv_batch_faulted());
    source_length=0;assert(!usb_drv_batch_start());
    assert(batch_stopped&&!usb_drv_batch_faulted());

    assert(!usb_drv_batch_deinit()&&!usb_drv_batch_faulted());
    printf("PASS: production batch pump + iAP sink recovery: a failed packet "
           "is restarted on the next tick; %u bounded restarts in 120 s of a "
           "silent host; stop/disable/exhausted are not faults\n",restarts);
    return 0;
}
'''

with tempfile.TemporaryDirectory() as d:
    p = Path(d)
    (p / 't.c').write_text(pre + pump + '\n' + recover + main)
    subprocess.run(['clang', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                    str(p / 't.c'), '-o', str(p / 't')], check=True)
    r = subprocess.run([str(p / 't')])
    if not order_ok:
        print('RED: usb_iap.c tick does not reach iap_audio_recover_stream() '
              'ahead of its control-wait early return')
    sys.exit(1 if r.returncode or not order_ok else 0)
