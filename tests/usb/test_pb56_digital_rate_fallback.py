"""Production announcement/SET_CUR/ACK/tick/packet path; synthetic host timing."""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = Path(os.environ.get('RODBOX_AUDIO_SOURCE', str(root / 'firmware-source/firmware/usbstack/iap/audio.c'))).read_text()
protocol = (root / 'firmware-source/firmware/usbstack/iap/libiap/iap.c').read_text()
def section(text, start, end):
    a = text.index(start)
    return text[a:text.index(end, a)]

pre = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#define IAPBool bool
#define iap_true true
#define iap_false false
#define IAPPhase_Auth 1
#define USB_BATCH_NON_NATIVE
#define USB_BATCH_SLOTS 2
#define HZ 100
#define SAMPR_48 48000
#define SAMPR_32 32000
#define ARRAYLEN(a) (sizeof(a)/sizeof((a)[0]))
#define array_size ARRAYLEN
#define RATE(f) samprs[f]
#define MIN(a,b) ((a)<(b)?(a):(b))
#define TIME_AFTER(a,b) ((long)((b)-(a))<0)
#define check_act(c,a,...) do{if(!(c)){a;}}while(0)
#define check_ret(c,r,...) do{if(!(c))return r;}while(0)
#define usb_log(...) ((void)0)
#define LOG(...) ((void)0)
#define ERROR(...) ((void)0)
#define swap_32(x) (x)
#define USB_LOG_IAP_STREAM_NOTHING 0
#define USB_LOG_IAP_STREAM_RATE_WAIT 1
#define USB_LOG_IAP_STREAM_AUDIO 2
#define PCM_DMAST_OK 0
#define PCM_DMAST_STARTED 1
#define IAPLingoID_DigitalAudio 10
#define IAPDigitalAudioCommandID_TrackNewAudioAttributes 4
#define IAPAckStatus_Success 0
struct IAPContext;
struct IAPActiveEvent{bool(*callback)(struct IAPContext*,struct IAPActiveEvent*);uint32_t sampr;};
struct IAPContext{bool waiting_for_audio_attrs_ack,send_busy;int32_t audio_attrs_trans_id,handling_trans_id;int phase;struct IAPActiveEvent active_events[2];};
struct IAPSpan{void*ptr;};
struct IAPTrackNewAudioAttributesPayload{uint32_t sample_rate,sound_check,volume_adjustment;};
struct Ack{int status;};
static struct IAPTrackNewAudioAttributesPayload payload;
static struct IAPContext ctx;
static const unsigned long samprs[]={48000,44100,32000};
static struct {struct {unsigned num_samprs;}caps;} iap_pcm_sink={{3}};
static bool accessory_ready=true,host_set_rate,enabled=true,track_attrs_sent,track_changed;
static bool exhausted,attrs_owed;
static int8_t set_freq,cur_freq,asked_freq,acked_freq,host_rate;
static long current_tick,announced_tick,attrs_owed_tick,host_rate_tick,host_rate_set_tick;
static int32_t attrs_owed_id;
static unsigned pcm_lock_count,starts;
static uint32_t count_silent,count_bytes,count_chunks,count_odd;
static uint8_t packet_count,logged_stream;
static const uint8_t* pulled_buf;
static size_t pulled_buf_cursor,pulled_buf_size;
static struct StagingBuffer {struct {uint8_t*ptr;}buf;size_t cursor;} staging_buffers[USB_BATCH_SLOTS+1];
#define zero_buffer staging_buffers[USB_BATCH_SLOTS]
static int staging_buffer_index;
static uint8_t stage_data[USB_BATCH_SLOTS+1][192],pcm[4096];
static void iap_audio_attrs_ack(bool);
static struct IAPContext*_iap_acquire_ctx(bool x){(void)x;return &ctx;}
static void _iap_release_ctx(void){}
static bool usb_iap2_audio_rate(unsigned long r){(void)r;return false;}
static bool iap_audio_enable(void){starts++;return true;}
static void offer_rates(unsigned n){(void)n;assert(0);}
static void iap_platform_take_sink(void){assert(0);}
static bool pcm_play_dma_complete_callback(int s,const void**p,size_t*n){(void)s;(void)p;(void)n;assert(0);return false;}
static void pcm_play_dma_status_callback(int s){(void)s;assert(0);}
static struct IAPSpan _iap_get_buffer_for_send_payload(struct IAPContext*c){(void)c;return(struct IAPSpan){&payload};}
static void*iap_span_alloc(struct IAPSpan*s,size_t n){assert(n==sizeof payload);return s->ptr;}
static int32_t _iap_next_trans_id(struct IAPContext*c){return ++c->audio_attrs_trans_id;}
static bool _iap_send_packet(struct IAPContext*c,int l,int cmd,int id,void*p){(void)c;(void)l;(void)cmd;(void)id;(void)p;return true;}
static void iap_platform_on_audio_attrs_ack(struct IAPContext*c,bool ok){(void)c;iap_audio_attrs_ack(ok);}
static bool push_active_event(struct IAPContext*c,struct IAPActiveEvent e){assert(!c->send_busy);return e.callback(c,&e);}
'''
ack = section(protocol, '                check_ret(ctx->waiting_for_audio_attrs_ack', '            check_ret(request->status == IAPAckStatus_Success')
ack = ack[:ack.rfind('            }')]
code = pre
code += section(protocol, 'static IAPBool process_select_sampr(', 'static IAPBool process_control_response(')
code += section(source, 'static void sink_set_freq(', 'static void sink_play(')
code += section(source, 'void iap_audio_attrs_ack(', 'static void sink_stop(').replace('void iap_audio_attrs_ack(', 'static void iap_audio_attrs_ack(')
code += source[source.index('bool iap_audio_set_sampr('):]
code += 'static int receive_ack(struct IAPContext*ctx,struct Ack*request){'+ack+'return 0;}\n'
code += r'''
static void packet(bool silence){
 const void*p=NULL;size_t n=0;size_t before=pulled_buf_cursor;
 size_t wanted=calc_packet_size(cur_freq>=0?RATE(cur_freq):0,packet_count);
 batch_get_more(&p,&n);assert(n==wanted);
 if(silence){assert(p==zero_buffer.buf.ptr&&pulled_buf_cursor==before);}
 else{assert(p!=zero_buffer.buf.ptr&&pulled_buf_cursor==before+192);for(size_t i=0;i<n;i++)assert(((const uint8_t*)p)[i]==0x5a);}
}
static void reset(void){
 memset(&ctx,0,sizeof ctx);memset(pcm,0x5a,sizeof pcm);memset(stage_data,0,sizeof stage_data);
 for(unsigned i=0;i<ARRAYLEN(staging_buffers);i++){staging_buffers[i].buf.ptr=stage_data[i];staging_buffers[i].cursor=0;}
 pulled_buf=pcm;pulled_buf_size=sizeof pcm;pulled_buf_cursor=0;staging_buffer_index=0;
 set_freq=cur_freq=acked_freq=1;asked_freq=-1;host_rate=-1;current_tick=100;
 attrs_owed=track_changed=exhausted=false;host_set_rate=true;starts=0;
 sink_set_freq(0);assert(ctx.waiting_for_audio_attrs_ack&&asked_freq==0&&payload.sample_rate==48000);
 packet(true);iap_audio_tick(); /* start real transaction timeout */
}
int main(void){
 /* Stale SET_CUR must not count as accepting the new announcement. */
 reset();assert(iap_audio_set_sampr(44100));assert(cur_freq==1&&starts==0);
 struct Ack ok={0};ctx.handling_trans_id=ctx.audio_attrs_trans_id-1;receive_ack(&ctx,&ok);
 assert(ctx.waiting_for_audio_attrs_ack);current_tick=150;iap_audio_tick();packet(true);
 ctx.handling_trans_id=ctx.audio_attrs_trans_id;receive_ack(&ctx,&ok);assert(acked_freq==0);
 current_tick=151;iap_audio_tick();
 if(cur_freq!=set_freq){fprintf(stderr,"FAIL: stale SET_CUR blocked half-second fallback after real ACK (host_set_rate=%d)\n",host_set_rate);return 1;}
 packet(false);
 /* No ACK: rate fallback alone must NOT release the PCM gate. */
 reset();assert(iap_audio_set_sampr(44100));current_tick=151;iap_audio_tick();assert(cur_freq==0);packet(true);
 current_tick=200;iap_audio_tick();packet(true);current_tick=201;iap_audio_tick();
 assert(!ctx.waiting_for_audio_attrs_ack&&acked_freq==0);packet(false);
 ctx.handling_trans_id=ctx.audio_attrs_trans_id;receive_ack(&ctx,&ok);packet(false);
 /* Valid late matching request is still accepted and may restart once. */
 assert(iap_audio_set_sampr(48000)&&host_set_rate&&starts==1);packet(false);
 assert(iap_audio_set_sampr(44100)&&cur_freq==0&&starts==1);packet(false);
 /* Explicit refusal remains silent even after rate fallback. */
 reset();assert(iap_audio_set_sampr(44100));struct Ack no={1};ctx.handling_trans_id=ctx.audio_attrs_trans_id;receive_ack(&ctx,&no);
 current_tick=301;iap_audio_tick();assert(cur_freq==0&&acked_freq==1);packet(true);
 assert(!iap_audio_set_sampr(12345));packet(true);
 puts("PASS: real announcement/SET_CUR/ACK/timeout/packet gate: stale rate cannot poison fallback; boundaries, silence-before-ACK, timeout, late ACK/matching request and refusal preserved");
}
'''
with tempfile.TemporaryDirectory() as d:
    p = Path(d)
    (p/'t.c').write_text(code)
    subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True)
    subprocess.run([str(p/'t')],check=True)
