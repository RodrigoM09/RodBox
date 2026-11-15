"""Captured Lexus subscriptions -> production decoder, track poll, notification and HID completion."""
from pathlib import Path
import ast,json,os,subprocess,tempfile
r=Path(__file__).resolve().parents[2];b=r/'firmware-source/firmware/usbstack/iap';lib=b/'libiap'
old=Path(os.environ.get('RODBOX_BASELINE_DIR','')) if os.environ.get('RODBOX_BASELINE_DIR') else None
def source(rel):
 p=old/rel if old and (old/rel).is_file() else r/'firmware-source'/rel
 return p.read_text()
def function(s,name):
 a=s.index(name);q=s.index('{',a);depth=1;z=q+1
 while depth:depth+=(s[z]=='{')-(s[z]=='}');z+=1
 return s[a:z]
def strip(s):return '\n'.join(l for l in s.splitlines() if not l.startswith('#include'))
s=source('firmware/usbstack/iap/libiap/iap.c');mapper=function(s,'static uint32_t play_stage_change_notification_set_mask_to_type_mask(')
a=s.index('        case IAPExtendedInterfaceCommandID_SetPlayStatusChangeNotification:');z=s.index('        case IAPExtendedInterfaceCommandID_PlayCurrentSelection:',a);handler=s[a:z]
notification=strip(source('firmware/usbstack/iap/libiap/notification.c'))
poll=function(source('firmware/usbstack/iap/platform.c'),'void iap_platform_refresh_track_state(')
keys=strip((r/'firmware-source/apps-ipod/database/path_key.c').read_text())
wrapper=function((r/'firmware-source/apps-ipod/iap/iap-library.c').read_text(),'uint64_t iap_library_key(')
h=(lib/'hid.c').read_text();hid=h[h.index('struct ReportSize {'):h.index('static struct ReportSize output_report_size_table_fs')]+h[h.index('static struct ReportSize input_report_size_table_hs'):h.index('static struct ReportSize output_report_size_table_hs')]+h[h.index('IAPBool iap_notify_send_complete('):]
# Reuse the already-tested buffered playback seams, not a second implementation of the poll.
tree=ast.parse((r/'tests/usb/test_iap_track_state_sync.py').read_text());pre=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='pre' for t in n.targets))
pre='#define TEST_REAL_IAP_LIBRARY_KEY 1\n'+pre
pre=pre.replace('#define MAX_PATH 260','#include "spec/hid.h"\n#define MAX_PATH 260\n#define check_act(c,a,...) do{if(!(c)){a;}}while(0)\n#define warn(...)\n#define array_size(a) (sizeof(a)/sizeof((a)[0]))\n#define min(a,b) ((a)<(b)?(a):(b))\nuint64_t iap_library_key(const char*);\nstatic unsigned uid_events,uid_order,status_queries;static uint64_t last_uid;\nstatic uint8_t staging[128];')
pre=pre.replace('(void)c;*p=status;return true;','(void)c;status_queries++;*p=status;return true;')
pkt=function(pre,'IAPBool _iap_send_packet(')
pkt=pkt.replace('sequence++;','sequence++;assert(!c->send_busy);assert((l==3?c->enabled_notifications_3:c->enabled_notifications_4)&(1u<<buffer[0]));\n if(l==4&&buffer[0]==10){assert(end-buffer==9);uint64_t u=0;for(unsigned n=1;n<9;n++)u=(u<<8)|buffer[n];assert(u==iap_library_key(current.path));last_uid=u;uid_events++;uid_order=sequence;}')
pkt=pkt.replace('return true;','return _iap_send_hid_reports(c,0,(size_t)(end-buffer));')
start=pre.index('IAPBool _iap_send_packet(');end=start+len(function(pre,'IAPBool _iap_send_packet('));pre=pre[:start]+pkt+pre[end:]
extra=r'''
int iap_platform_send_hid_report(struct IAPContext*c,const void*p,size_t n){assert(c->send_busy&&p==staging);return (int)n;}
#define read_request(T) struct T*request=(struct T*)request_span->ptr;check_ret(request_span->size==sizeof(*request),-1)
static int32_t ipod_ack_ext(uint16_t cmd,int status,struct IAPSpan*out){(void)cmd;(void)status;(void)out;return 0;}
static void advance(struct IAPContext*c,unsigned n){for(unsigned k=0;k<n;k++){iap_notify_track_time_position(c,k*100);assert(iap_periodic_tick(c));iap_notify_track_time_position(c,k*100+50);if(c->send_busy)assert(iap_notify_send_complete(c));}}
static void clear_events(void){reset();uid_events=uid_order=0;}
'''
fixture=json.loads((r/'tests/usb/fixtures/lexus_notification_subscriptions.json').read_text());raw3=bytes.fromhex(fixture['display_remote_payload_hex']);raw4=bytes.fromhex(fixture['extended_interface_payload_hex']);expected=sum(1<<x for x in fixture['expected_extended_event_types'])
main=r'''
int main(void){
 struct Platform p={0};struct IAPContext c={.platform=&p,.send_buf=buffer,.hid_send_staging_buf=staging};
 uint8_t q[]={RAW4};struct IAPSpan in={q,sizeof(q)},out={buffer,sizeof buffer};
 c.enabled_notifications_3=MASK3;
 assert(subscribe(&c,&in,&out)==0);
 assert(c.enabled_notifications_4==EXPECTED); /* PB54 silently drops the Lexus UID/caps bits. */
 advance(&c,30);assert(uid_events==1&&art_events==1&&clock_events);assert(!index_events&&!queue_events);assert(uid_order>0);
 uint64_t first=last_uid;clear_events();status.track_index=1;strcpy(current.path,"/Music/Artist A/Album A/two.flac");
 /* Local skip, no PlayControl or metadata query: both requested events must arrive. */
 advance(&c,30);assert(uid_events==1&&art_events==1&&clock_events&&last_uid!=first);assert(!index_events&&!queue_events);
 first=last_uid;clear_events();status.track_caps=0;strcpy(current.path,"/Music/Artist B/Album B/first.flac");
 /* Another artist/album reuses queue index/count; UID still has to change. */
 advance(&c,30);assert(uid_events==1&&art_events==1&&last_uid!=first);assert(!index_events&&!queue_events);
 clear_events();advance(&c,30);assert(!uid_events&&!art_events&&clock_events);
 /* Pure UID subscriptions must activate the buffered poll without querying art. */
 c.enabled_notifications_3=0;c.enabled_notifications_4=play_stage_change_notification_set_mask_to_type_mask(0x100);
 clear_events();unsigned queries=status_queries;status.track_index=2;strcpy(current.path,"/Music/Artist B/Album B/second.flac");advance(&c,30);
 assert(uid_events==1&&!art_events&&status_queries==queries);
 /* A later callback-free transition models automatic advance, not a physical car test. */
 first=last_uid;clear_events();status.track_index=3;strcpy(current.path,"/Music/Artist B/Album B/third.flac");advance(&c,30);assert(uid_events==1&&last_uid!=first);
 /* UID uses the exact metadata/library key, including path/case normalization. */
 assert(iap_library_key("/<HDD0>/Music/Artist B/Album B/third.flac")==last_uid);
 assert(iap_library_key("/MUSIC/ARTIST B/ALBUM B/THIRD.FLAC")==last_uid);
 /* Backpressure retains the latest identity until HID can send it. */
 clear_events();c.send_busy=1;status.track_index=4;strcpy(current.path,"/Music/Artist C/Album C/first.flac");
 for(unsigned k=0;k<10;k++){iap_notify_track_time_position(&c,k*100);assert(iap_periodic_tick(&c));}assert(!uid_events);
 c.send_busy=0;advance(&c,30);assert(uid_events==1&&last_uid==iap_library_key(current.path));
 c.enabled_notifications_4=0;clear_events();unsigned prior=reads;advance(&c,30);assert(!uid_events&&!art_events&&reads==prior);
 puts("PASS: captured Lexus 0x18d/0x901 subscription decoder -> buffered poll -> exact 9-byte UID and 5-byte caps -> asynchronous HID; local/callback-free advance, same-slot artist changes, stable state, UID-only mask, backpressure and canonical library key");
}
'''.replace('RAW4',','.join(str(x) for x in raw4)).replace('MASK3',str(int.from_bytes(raw3,'big'))).replace('EXPECTED',str(expected))
subscribe='static int subscribe(struct IAPContext*ctx,struct IAPSpan*request_span,struct IAPSpan*response_span){const uint16_t command=IAPExtendedInterfaceCommandID_SetPlayStatusChangeNotification;switch(command){'+handler+'}return -1;}\n'
code=pre+keys+wrapper+mapper+extra+subscribe+poll+notification+hid+main
with tempfile.TemporaryDirectory() as d:
 q=Path(d);(q/'t.c').write_text(code)
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-I',str(lib),str(q/'t.c'),'-o',str(q/'t')],check=True)
 subprocess.run([str(q/'t')],check=True)
