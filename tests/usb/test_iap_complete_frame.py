from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[2];s=(r/'firmware-source/firmware/usbstack/iap/libiap/hid.c').read_text();a=s.index('static size_t complete_frame_size');b=s.index('\nIAPBool iap_notify_send_complete',a)
pre=r'''
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <string.h>
#include <stdio.h>
#define IAP_SYNC_BYTE 0xff
#define IAP_SOF_BYTE 0x55
#define HID_BUFFER_SIZE 1024
#define iap_false false
#define iap_true true
#define check_ret(c,r,...) do{if(!(c))return r;}while(0)
#define check_act(c,a,...) do{if(!(c)){a;}}while(0)
#define warn(...) ((void)0)
typedef bool IAPBool;
enum {IAPHIDReportLinkControlBits_Continue=1,IAPHIDReportLinkControlBits_MoreToFollow=2};
struct IAPHIDReport {uint8_t report_id,link_control,data[];};
struct IAPContext {struct {bool ignore_hid_report_id;} opts;size_t hid_recv_buf_cursor;uint8_t hid_recv_buf[1024];};
static int calls;static size_t received;
static int find_output_report_size(struct IAPContext*c,uint8_t id){(void)c;(void)id;return -1;}
static bool _iap_feed_packet(struct IAPContext*c,const uint8_t*d,size_t n){(void)c;(void)d;calls++;received=n;return true;}
'''
main=r'''
int main(void){
 uint8_t frame[]={0xff,0x55,3,0,0x39,1,0xc3};
 assert(complete_frame_size(frame,sizeof frame)==7);
 for(size_t n=0;n<7;n++)assert(complete_frame_size(frame,n)==0);
 frame[6]^=1;assert(!complete_frame_size(frame,7));frame[6]^=1;
 struct IAPContext c={.opts={true}};uint8_t report[9]={0,2};memcpy(report+2,frame,7);
 assert(iap_feed_hid_report(&c,report,9));assert(calls==1&&received==7&&c.hid_recv_buf_cursor==0);
 /* Real fragmentation: first fragment must not dispatch; final one does. */
 calls=0;assert(iap_feed_hid_report(&c,report,5));assert(calls==0&&c.hid_recv_buf_cursor==3);
 uint8_t last[6]={0,1};memcpy(last+2,frame+3,4);
 assert(iap_feed_hid_report(&c,last,6));assert(calls==1&&received==7);
 /* A new first frame replaces abandoned data before checking capacity. */
 c.hid_recv_buf_cursor=1023;assert(iap_feed_hid_report(&c,report,9));assert(calls==2);
 uint8_t big[306]={0xff,0x55,0,1,44};unsigned sum=1+44;
 for(int i=5;i<305;i++){big[i]=(uint8_t)i;sum+=big[i];}big[305]=(uint8_t)-sum;
 assert(complete_frame_size(big,306)==306);
 for(size_t n=0;n<306;n++)assert(!complete_frame_size(big,n));
 uint8_t br[308]={0,2};memcpy(br+2,big,306);assert(iap_feed_hid_report(&c,br,308));assert(received==306);
 puts("PASS: complete, bad checksum, truncated, fragmented, abandoned and long frames; actual receive body");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(pre+s[a:b]+main);subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True);subprocess.run([str(p/'t')],check=True)
