"""Playback-state reconciliation must refresh a car without a remote skip/query."""
from pathlib import Path
import os,re,subprocess,tempfile
r=Path(__file__).resolve().parents[2];b=r/'firmware-source/firmware/usbstack/iap';lib=b/'libiap'
notification=Path(os.environ.get('RODBOX_NOTIFICATION_SOURCE',str(lib/'notification.c'))).read_text()
notification='\n'.join(l for l in notification.splitlines() if not l.startswith('#include'))
s=Path(os.environ.get('RODBOX_PLATFORM_SOURCE',str(b/'platform.c'))).read_text()
name='void iap_platform_refresh_track_state('
if name in s:
 start=s.index(name);brace=s.index('{',start);depth=1;end=brace+1
 while depth:
  depth+=(s[end]=='{')-(s[end]=='}');end+=1
 poll=s[start:end]
else:poll='void iap_platform_refresh_track_state(struct IAPContext*c){(void)c;}'
pre=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "iap.h"
#include "endian.h"
#define MAX_PATH 260
#define AUDIO_STATUS_PLAY 1
#define AUDIO_STATUS_PAUSE 2
#define check_ret(c,r,...) do{if(!(c))return r;}while(0)
#define print(...)
struct mp3entry{char path[MAX_PATH];};
struct Platform{bool observed_track_valid;uint32_t observed_track_index,observed_track_count;char observed_track_path[MAX_PATH];};
static struct mp3entry current={"/Music/Artist A/Album A/one.flac"};
static struct IAPPlatformPlayStatus status={.state=IAPIPodStatePlayStatus_Playing,.track_count=7,.track_index=0,.track_caps=4};
static bool snapshot_ok=true,changing=false,stop_during_snapshot=false;static unsigned reads,index_events,art_events,queue_events,clock_events;static unsigned sequence,queue_order,index_order;
static int audio_status(void){return status.state==IAPIPodStatePlayStatus_PlaybackStopped?0:AUDIO_STATUS_PLAY|(status.state==IAPIPodStatePlayStatus_PlaybackPaused?AUDIO_STATUS_PAUSE:0);}
static int playlist_get_display_index(void){if(changing){changing=false;return (int)status.track_index+2;}return (int)status.track_index+1;}
static int playlist_amount(void){return status.track_count;}
static unsigned forbidden_snapshot_reads;
static bool audio_current_track_copy(struct mp3entry*out){(void)out;forbidden_snapshot_reads++;assert(!"forbidden non-buffered snapshot accessor");return false;}
static bool audio_peek_buffered_track(struct mp3entry*out,int offset){assert(offset==0);reads++;if(!snapshot_ok)return false;*out=current;if(stop_during_snapshot){stop_during_snapshot=false;status.state=IAPIPodStatePlayStatus_PlaybackStopped;}return true;}
#define strlcpy test_strlcpy
static size_t strlcpy(char*d,const char*s,size_t n){size_t k=strlen(s);if(n){size_t c=k<n-1?k:n-1;memcpy(d,s,c);d[c]=0;}return k;}
static uint8_t buffer[256];
#ifndef TEST_REAL_IAP_LIBRARY_KEY
/* This older test does not subscribe to UID; the captured-mask replay uses the real key. */
static uint64_t iap_library_key(const char*path){(void)path;return 1;}
#endif
struct IAPSpan _iap_get_buffer_for_send_payload(struct IAPContext*c){(void)c;return(struct IAPSpan){buffer,sizeof buffer};}
int32_t _iap_next_trans_id(struct IAPContext*c){return ++c->trans_id;}
void*iap_span_alloc(struct IAPSpan*s,size_t n){if(s->size<n)return NULL;void*p=s->ptr;s->ptr+=n;s->size-=n;return p;}
IAPBool iap_platform_get_play_status(struct IAPContext*c,struct IAPPlatformPlayStatus*p){(void)c;*p=status;return true;}
IAPBool _iap_send_packet(struct IAPContext*c,uint8_t l,uint16_t cmd,int32_t tid,uint8_t*end){
 (void)c;(void)cmd;(void)tid;assert((l==3||l==4)&&end>buffer);sequence++;
 uint32_t v=end-buffer==5?((uint32_t)buffer[1]<<24)|((uint32_t)buffer[2]<<16)|((uint32_t)buffer[3]<<8)|buffer[4]:0;
 if(buffer[0]==1){assert(v==status.track_index);index_events++;index_order=sequence;}
 if((l==3&&buffer[0]==17)||(l==4&&buffer[0]==13)){assert(v==status.track_caps);art_events++;}
 if((l==3&&buffer[0]==18)||(l==4&&buffer[0]==14)){assert(v==status.track_count);queue_events++;queue_order=sequence;}
 if((l==3&&buffer[0]==0)||(l==4&&buffer[0]==4))clock_events++;
 return true;
}
static void drain(struct IAPContext*c){for(int n=0;n<50;n++){iap_notify_track_time_position(c,n*100);assert(iap_periodic_tick(c));}}
static void reset(void){index_events=art_events=queue_events=clock_events=sequence=queue_order=index_order=0;}
'''
main=r'''
int main(void){
 struct Platform p={0};struct IAPContext c={.platform=&p};
 c.enabled_notifications_3=(1u<<0)|(1u<<1)|(1u<<17)|(1u<<18);
 /* PB53 updates the timer but has no track event if its callback is missed. */
 drain(&c);assert(index_events&&art_events&&queue_events&&clock_events);
 reset();status.track_index=1;strcpy(current.path,"/Music/Artist A/Album A/two.flac");
 drain(&c);assert(index_events&&art_events&&clock_events);assert(!queue_events);
 /* Another artist/album reuses the queue index and amount. */
 reset();strcpy(current.path,"/Music/Artist B/Album B/first.flac");status.track_caps=0;
 drain(&c);assert(index_events&&art_events&&queue_events);assert(queue_order<index_order);
 /* Stable playback must not repeatedly invalidate the queue or reload art. */
 reset();drain(&c);assert(!index_events&&!art_events&&!queue_events&&clock_events);
 /* A bad snapshot must be retried, not committed as the current identity. */
 reset();snapshot_ok=false;status.track_index=2;strcpy(current.path,"/Music/Artist B/Album B/next.flac");
 drain(&c);assert(!index_events&&!art_events);snapshot_ok=true;drain(&c);assert(index_events&&art_events);
 /* Stopped playback does not emit a fabricated current track; resume refreshes. */
 reset();status.state=IAPIPodStatePlayStatus_PlaybackStopped;drain(&c);assert(!index_events&&!art_events);
 status.state=IAPIPodStatePlayStatus_Playing;drain(&c);assert(index_events&&art_events);
 /* Stop during a successful copy must invalidate even a previously observed identity. */
 reset();assert(p.observed_track_valid);stop_during_snapshot=true;iap_platform_refresh_track_state(&c);
 assert(!p.observed_track_valid);assert(!index_events&&!art_events&&!queue_events);
 status.state=IAPIPodStatePlayStatus_Playing;drain(&c);assert(p.observed_track_valid&&index_events&&art_events&&queue_events);
 /* Paused playback still has a current buffered identity; it is not stopped. */
 reset();status.state=IAPIPodStatePlayStatus_PlaybackPaused;strcpy(current.path,"/Music/Artist B/Album B/paused.flac");
 drain(&c);assert(p.observed_track_valid&&index_events&&art_events&&queue_events);
 reset();drain(&c);assert(p.observed_track_valid&&!index_events&&!art_events&&!queue_events);
 status.state=IAPIPodStatePlayStatus_Playing;
 /* Never force events an accessory has not subscribed to. */
 reset();c.enabled_notifications_3=1u;unsigned prior=reads;drain(&c);assert(!index_events&&!art_events&&!queue_events&&reads==prior);
 /* ExtendedInterface-only accessories get the same fallback, not forced lingo 3. */
 reset();c.enabled_notifications_3=0;c.enabled_notifications_4=(1u<<1)|(1u<<4)|(1u<<13)|(1u<<14);
 status.track_index=3;strcpy(current.path,"/Music/Artist C/Album C/next.flac");
 drain(&c);assert(index_events&&art_events&&queue_events&&clock_events);assert(queue_order<index_order);
 /* A queue moving during the snapshot must not commit a mixed identity. */
 reset();status.track_index=4;changing=true;assert(iap_periodic_tick(&c));assert(!index_events);
 drain(&c);assert(index_events&&art_events);
 /* Waiting for the existing audio-attributes ACK must still suppress polling. */
 reset();c.waiting_for_audio_attrs_ack=1;prior=reads;drain(&c);assert(reads==prior&&!index_events);
 assert(!forbidden_snapshot_reads);
 puts("PASS: production USB tick + buffered-only track snapshot reconciles current title/art identity; queue order, retry, stable/paused/stopped state, stop-during-copy, subscriptions and ACK gating");
}
'''
with tempfile.TemporaryDirectory() as d:
 q=Path(d);(q/'t.c').write_text(pre+poll+notification+main)
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-I',str(lib),str(q/'t.c'),'-o',str(q/'t')],check=True)
 subprocess.run([str(q/'t')],check=True)

# The static platform survives disconnects; a new context must not reuse its identity.
driver=(b.parent/'usb_iap.c').read_text()
driver=re.sub(r'/\*.*?\*/|//[^\n]*','',driver,flags=re.S)
start=driver.index('static int usb_iap_init_connection(void)')
brace=driver.index('{',start);depth=1;end=brace+1
while depth:
 depth+=(driver[end]=='{')-(driver[end]=='}');end+=1
connection=driver[brace:end]
reset=re.search(r'\bplatform\s*\.\s*observed_track_valid\s*=\s*false\s*;',connection)
assert reset is not None,'connection must explicitly reset platform.observed_track_valid'
assert reset.end()<connection.index('iap_init_ctx('),'reset must precede context initialization'
print('PASS: connection resets observed identity before iap_init_ctx')
