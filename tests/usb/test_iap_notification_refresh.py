"""Exercise real notification source and packet layouts with a controlled playback seam."""
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[2];base=r/'firmware-source/firmware/usbstack/iap/libiap'
s=(base/'notification.c').read_text();s='\n'.join(l for l in s.splitlines() if not l.startswith('#include'))
pre=r'''
#include <assert.h>
#include <stdbool.h>
#include <string.h>
#include <stdio.h>
#include "iap.h"
#include "endian.h"
#define check_ret(c,r,...) do{if(!(c))return r;}while(0)
#define print(...)
static uint8_t buffer[256],packets[64][8],lingoes[64];static size_t sizes[64];static unsigned sent,queries;
static struct IAPPlatformPlayStatus status={.state=IAPIPodStatePlayStatus_Playing,.track_index=0,.track_count=10,.track_caps=4};
static bool status_ok=true,send_ok=true;
struct IAPSpan _iap_get_buffer_for_send_payload(struct IAPContext*c){(void)c;return(struct IAPSpan){buffer,sizeof buffer};}
int32_t _iap_next_trans_id(struct IAPContext*c){return ++c->trans_id;}
IAPBool _iap_send_packet(struct IAPContext*c,uint8_t l,uint16_t cmd,int32_t tid,uint8_t*end){
 (void)c;assert(tid>0);assert(cmd==(l==3?IAPDisplayRemoteCommandID_RemoteEventNotification:IAPExtendedInterfaceCommandID_PlayStatusChangeNotification));
 if(!send_ok)return iap_false;
 assert(sent<64&&end-buffer<=8);sizes[sent]=end-buffer;memcpy(packets[sent],buffer,end-buffer);lingoes[sent++]=l;return iap_true;
}
void* iap_span_alloc(struct IAPSpan*s,size_t n){if(s->size<n)return NULL;void*p=s->ptr;s->ptr+=n;s->size-=n;return p;}
IAPBool iap_platform_get_play_status(struct IAPContext*c,struct IAPPlatformPlayStatus*p){(void)c;queries++;*p=status;return status_ok;}
static void drain(struct IAPContext*c){for(int n=0;n<40;n++)assert(iap_periodic_tick(c));}
static unsigned find(unsigned start,unsigned l,unsigned type){for(unsigned n=start;n<sent;n++)if(lingoes[n]==l&&packets[n][0]==type)return n;return 999;}
'''
main=r'''
int main(void){
 struct IAPContext c={0};
 c.enabled_notifications_3=(1u<<IAPIPodStateType_TrackPlaybackIndex)|(1u<<IAPIPodStateType_TrackCaps)|(1u<<IAPIPodStateType_PlaybackEngineContents);
 c.enabled_notifications_4=(1u<<IAPStatusChangeNotificationType_TrackIndex)|(1u<<IAPStatusChangeNotificationType_TrackCapsChanged)|(1u<<IAPStatusChangeNotificationType_PlaybackEngineContentsChanged);
 iap_notify_tracks_count(&c,10);iap_notify_track_playback_index(&c,0);drain(&c);
 unsigned art=find(0,3,IAPIPodStateType_TrackCaps);assert(art<sent&&sizes[art]==5&&packets[art][4]==4);
 assert(find(0,4,IAPStatusChangeNotificationType_TrackCapsChanged)<sent);
 assert(find(0,3,IAPIPodStateType_PlaybackEngineContents)<find(0,3,IAPIPodStateType_TrackPlaybackIndex));
 assert(find(0,4,IAPStatusChangeNotificationType_PlaybackEngineContentsChanged)<find(0,4,IAPStatusChangeNotificationType_TrackIndex));
 unsigned start=sent;
 /* Album B reuses index/count; its missing art must clear album A's bit. */
 status.track_caps=0;iap_notify_tracks_count(&c,10);iap_notify_track_playback_index(&c,0);drain(&c);
 art=find(start,3,IAPIPodStateType_TrackCaps);assert(art<sent&&packets[art][4]==0);
 assert(find(start,4,IAPStatusChangeNotificationType_PlaybackEngineContentsChanged)<find(start,4,IAPStatusChangeNotificationType_TrackIndex));
 /* Backpressure and attribute negotiation must defer, not lose refresh. */
 start=sent;status.track_caps=4;status.track_index=2;iap_notify_track_playback_index(&c,2);
 c.waiting_for_audio_attrs_ack=1;drain(&c);assert(sent==start);c.waiting_for_audio_attrs_ack=0;
 c.send_busy=1;drain(&c);assert(sent==start);c.send_busy=0;drain(&c);
 art=find(start,4,IAPStatusChangeNotificationType_TrackCapsChanged);assert(art<sent&&packets[art][4]==4);
 unsigned old=queries;drain(&c);assert(queries==old); /* no repeated disk polling */
 struct IAPContext quiet={0};start=sent;iap_notify_track_playback_index(&quiet,0);drain(&quiet);assert(sent==start&&queries==old);
 puts("PASS: real packets refresh artwork for reused indices; queue-before-index order, subscriptions, backpressure, negotiation and bounded polling");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(pre+s+main)
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I',str(base),str(p/'t.c'),'-o',str(p/'t')],check=True)
 subprocess.run([str(p/'t')],check=True)
