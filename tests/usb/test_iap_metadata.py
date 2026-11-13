from pathlib import Path
import subprocess,tempfile,re
r=Path(__file__).resolve().parents[2];base=r/'firmware-source/firmware/usbstack/iap/libiap'
s=(base/'iap.c').read_text()
cb=s[s.index('static IAPBool send_metadata_cb'):s.index('static int32_t ipod_ack(')]
a=s.index('        case IAPExtendedInterfaceCommandID_GetDBTrackInfo:')
b=s.index('        case IAPExtendedInterfaceCommandID_GetTrackArtworkTimes:',a)
handler=s[a:b]
span=(base/'span.c').read_text()
span='\n'.join(l for l in span.splitlines() if not l.startswith('#include'))
pre=r"""
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#define check_ret(c,r,...) do{if(!(c))return r;}while(0)
#include "unaligned.h"
#include "span.h"
#define swap_8(x) (x)
#define swap_16(x) __builtin_bswap16(x)
#define swap_32(x) __builtin_bswap32(x)
#define swap_64(x) __builtin_bswap64(x)
enum {IAPLingoID_ExtendedInterface=4,IAPExtendedInterfaceCommandID_GetDBTrackInfo=0x40,
 IAPExtendedInterfaceCommandID_GetPBTrackInfo=0x42,IAPExtendedInterfaceCommandID_RetDBTrackInfo=0x41,
 IAPExtendedInterfaceCommandID_RetPBTrackInfo=0x43,IAPAckStatus_EBadParameter=4,IAPAckStatus_ECommandFailed=2};
struct IAPContext {
 uint32_t metadata_index,metadata_end,metadata_mask;int metadata_trans_id,handling_trans_id;
 unsigned metadata_reply,metadata_type;bool metadata_database;
 IAPBool(*on_send_complete)(struct IAPContext*);
};
static uint8_t buffer[256],packets[32][256];static size_t lengths[32];static unsigned calls;
static unsigned total=3;
static struct IAPSpan _iap_get_buffer_for_send_payload(struct IAPContext*c){(void)c;return (struct IAPSpan){buffer,sizeof buffer};}
static bool iap_platform_track_count(struct IAPContext*c,bool db,uint32_t*n){(void)c;(void)db;*n=total;return true;}
static bool _iap_send_packet(struct IAPContext*c,int l,int cmd,int tid,uint8_t*end){
 assert(l==4&&cmd==(c->metadata_database?0x41:0x43)&&tid==123);
 assert(calls<32);lengths[calls]=end-buffer;memcpy(packets[calls++],buffer,end-buffer);return true;
}
static bool iap_platform_track_field(struct IAPContext*c,bool db,uint32_t idx,unsigned type,struct IAPSpan*out){
 (void)c;(void)db;assert(idx<total);
 if(type>=1&&type<=5)return iap_span_append(out,"Name",5);
 if(type==7)return iap_span_write_64(out,0x1122334455667788ULL);
 if(type==13)return iap_span_write_16(out,258);
 return iap_span_write_32(out,0x12345678);
}
"""
main=r"""
int main(void){
 uint8_t q[]={0,0,0,1,0,0,0,2,0xbf,0x20,0,0};
 struct IAPContext c={.handling_trans_id=123};struct IAPSpan out={buffer,256},in={q,12};
 assert(handle(&c,0x40,&in,&out)==0);assert(!out.ptr);
 while(c.on_send_complete){IAPBool(*f)(struct IAPContext*)=c.on_send_complete;c.on_send_complete=0;assert(f(&c));}
 assert(calls==16);unsigned types[]={0,1,2,3,4,5,7,13};
 for(unsigned n=0;n<16;n++){assert(packets[n][3]==1+n/8);assert(packets[n][4]==types[n%8]);}
 assert(lengths[6]==13&&packets[6][5]==0x11&&packets[6][12]==0x88);
 assert(lengths[7]==7&&packets[7][5]==1&&packets[7][6]==2);
 for(size_t n=0;n<9;n++){in=(struct IAPSpan){q,n};assert(handle(&c,0x40,&in,&out)<0);}
 q[8]=0;q[9]=0;in=(struct IAPSpan){q,12};assert(handle(&c,0x40,&in,&out)<0);
 q[9]=0x80;in=(struct IAPSpan){q,12};assert(handle(&c,0x40,&in,&out)<0);
 q[8]=2;q[9]=0;q[3]=3;in=(struct IAPSpan){q,12};assert(handle(&c,0x40,&in,&out)<0);
 q[3]=1;q[4]=0x7f;in=(struct IAPSpan){q,12};assert(handle(&c,0x40,&in,&out)<0);
 memset(q+4,0xff,4);in=(struct IAPSpan){q,9};calls=0;
 assert(handle(&c,0x42,&in,&out)==0);
 while(c.on_send_complete){IAPBool(*f)(struct IAPContext*)=c.on_send_complete;c.on_send_complete=0;assert(f(&c));}
 assert(calls==2);
 puts("PASS: actual metadata handler, callback ordering, exact wire bytes, odd-offset writes, masks/ranges/truncation");
}
"""
span=span.replace('__attribute__((alias("iap_span_read")))', '{ return (void*)iap_span_read(span, count); }')
code=pre+span+'\n'+cb+'\nstatic int handle(struct IAPContext*ctx,unsigned command,struct IAPSpan*request_span,struct IAPSpan*response_span){switch(command){'+handler+'}return -99;}\n'+main
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(code)
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I',str(base),str(p/'t.c'),'-o',str(p/'t')],check=True)
 subprocess.run([str(p/'t')],check=True)
