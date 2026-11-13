from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[2]
s=(r/'firmware-source/firmware/usbstack/iap/libiap/iap.c').read_text()
a=s.index('static IAPBool process_select_sampr(');b=s.index('static IAPBool process_control_response(',a)
ack=s[s.index('                check_ret(ctx->waiting_for_audio_attrs_ack'):s.index('            check_ret(request->status == IAPAckStatus_Success',s.index('                check_ret(ctx->waiting_for_audio_attrs_ack'))]
# Strip the closing if(request->id...) brace; exercise its body.
ack=ack[:ack.rfind('            }')]
t=(r/'firmware-source/firmware/usbstack/iap/audio.c').read_text();ta=t.index('void iap_audio_tick(void)');tb=t.index('    if(track_changed',ta)
pre=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#define IAPBool bool
#define iap_true true
#define iap_false false
#define check_ret(c,r,...) do{if(!(c))return r;}while(0)
#define array_size(a) (sizeof(a)/sizeof((a)[0]))
#define swap_32(x) (x)
#define IAPLingoID_DigitalAudio 10
#define IAPDigitalAudioCommandID_TrackNewAudioAttributes 4
#define IAPAckStatus_Success 0
struct IAPContext;
struct IAPActiveEvent{bool(*callback)(struct IAPContext*,struct IAPActiveEvent*);uint32_t sampr;};
struct IAPContext{bool waiting_for_audio_attrs_ack,send_busy;int32_t audio_attrs_trans_id,handling_trans_id;struct IAPActiveEvent active_events[2];};
struct IAPSpan{void*ptr;};
struct IAPTrackNewAudioAttributesPayload{uint32_t sample_rate,sound_check,volume_adjustment;};
static struct IAPTrackNewAudioAttributesPayload payload;
static struct IAPContext ctx;
static unsigned sent,acks;static bool fail,ack_ok;static int serial;
static struct IAPSpan _iap_get_buffer_for_send_payload(struct IAPContext*c){(void)c;return(struct IAPSpan){&payload};}
static void*iap_span_alloc(struct IAPSpan*s,size_t n){assert(n==sizeof payload);return s->ptr;}
static int _iap_next_trans_id(struct IAPContext*c){(void)c;return ++serial;}
static bool _iap_send_packet(struct IAPContext*c,int l,int cmd,int id,void*p){(void)c;(void)l;(void)cmd;(void)id;(void)p;sent++;return !fail;}
static void iap_platform_on_audio_attrs_ack(struct IAPContext*c,bool ok){(void)c;acks++;ack_ok=ok;}
static bool push_active_event(struct IAPContext*c,struct IAPActiveEvent e){if(!c->send_busy)return e.callback(c,&e);c->active_events[0]=e;return true;}
struct Ack{int status;};
#define HZ 100
#define TIME_AFTER(a,b) ((long)((b)-(a))<0)
#define ERROR(...) ((void)0)
static bool attrs_owed;static long attrs_owed_tick,current_tick;static int32_t attrs_owed_id;
static struct IAPContext*_iap_acquire_ctx(bool x){(void)x;return &ctx;}
static void _iap_release_ctx(void){}
static void iap_audio_attrs_ack(bool ok){iap_platform_on_audio_attrs_ack(&ctx,ok);}
'''
main=r'''
int main(void){
 assert(iap_select_sampr(&ctx,48000)&&ctx.waiting_for_audio_attrs_ack&&sent==1);
 int first=ctx.audio_attrs_trans_id;
 assert(!iap_select_sampr(&ctx,44100)&&sent==1); /* no overlapping transaction */
 struct Ack ok={0};ctx.handling_trans_id=first-1;receive_ack(&ctx,&ok);
 assert(ctx.waiting_for_audio_attrs_ack&&acks==0); /* stale ack cannot unblock */
 ctx.handling_trans_id=first;receive_ack(&ctx,&ok);assert(!ctx.waiting_for_audio_attrs_ack&&acks==1&&ack_ok);
 ctx.send_busy=true;assert(iap_select_sampr(&ctx,32000));assert(iap_select_sampr(&ctx,44100));
 assert(ctx.active_events[0].sampr==44100&&!ctx.active_events[1].callback);
 ctx.send_busy=false;struct IAPActiveEvent e=ctx.active_events[0];ctx.active_events[0].callback=NULL;
 assert(e.callback(&ctx,&e)&&payload.sample_rate==44100&&ctx.waiting_for_audio_attrs_ack);
 current_tick=100;iap_audio_tick();assert(attrs_owed);
 current_tick=201;iap_audio_tick();assert(!ctx.waiting_for_audio_attrs_ack&&!attrs_owed&&ack_ok);
 unsigned before=acks;ctx.handling_trans_id=ctx.audio_attrs_trans_id;receive_ack(&ctx,&ok);assert(acks==before);
 fail=true;assert(!iap_select_sampr(&ctx,48000)&&!ctx.waiting_for_audio_attrs_ack&&!ack_ok);
 fail=false;assert(iap_select_sampr(&ctx,48000));iap_audio_tick();
 ctx.handling_trans_id=ctx.audio_attrs_trans_id;receive_ack(&ctx,&ok);
 current_tick=280;assert(iap_select_sampr(&ctx,32000));iap_audio_tick();
 current_tick=302;iap_audio_tick();assert(ctx.waiting_for_audio_attrs_ack); /* new timer */
 puts("PASS: serialized/coalesced rates, failed send cleanup, correlated/stale/late ACKs, unified timeout and fresh transaction deadline");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(pre+s[a:b]+'static int receive_ack(struct IAPContext*ctx,struct Ack*request){'+ack+'return 0;}'+t[ta:tb]+'}\n'+main)
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True)
 subprocess.run([str(p/'t')],check=True)
