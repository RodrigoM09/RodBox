from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[2];s=(r/'firmware-source/firmware/usbstack/iap/libiap/iap.c').read_text()
a=s.index('        case IAPDisplayRemoteCommandID_GetTrackArtworkTimes: {')
b=s.index('\n        } break;',a)+len('\n        } break;')
body=s[a:b]
a=s.index('        case IAPExtendedInterfaceCommandID_GetTrackArtworkTimes: {')
b=s.index('\n        } break;',a)+len('\n        } break;')
ext=s[a:b]
pre=r"""
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>
#define check_ret(c,r,...) do{if(!(c))return r;}while(0)
#define swap_16(x) __builtin_bswap16(x)
#define swap_32(x) __builtin_bswap32(x)
#define iap_false 0
#define IAP_ARTWORK_FORMAT_ID 7
#define IAPIPodStateTrackCapBits_HasAlbumArts 8
enum{IAPDisplayRemoteCommandID_GetTrackArtworkTimes=0x17,IAPDisplayRemoteCommandID_RetTrackArtworkTimes=0x18,
 IAPExtendedInterfaceCommandID_GetTrackArtworkTimes=0x2a,IAPExtendedInterfaceCommandID_RetTrackArtworkTimes=0x2b,
 IAPLingoID_DisplayRemote=3,IAPAckStatus_EBadParameter=4};
struct IAPContext{int unused;};struct IAPSpan{uint8_t*ptr;size_t size;};
struct IAPGetTrackArtworkTimesPayload{uint32_t track_index;uint16_t format_id,artwork_index,artwork_count;}__attribute__((packed));
struct IAPPlatformTrackInfo{uint32_t*caps;};static bool art=true;
#define read_request(T) check_ret(request_span->size>=sizeof(struct T),-4);const struct T*request=(const void*)request_span->ptr
static bool iap_platform_get_indexed_track_info(struct IAPContext*c,uint32_t i,struct IAPPlatformTrackInfo*t){(void)c;*t->caps=art?8:0;return i<3;}
static void*iap_span_alloc(struct IAPSpan*s,size_t n){if(s->size<n)return NULL;void*p=s->ptr;s->ptr+=n;s->size-=n;return p;}
"""
func='static int32_t handle_command(struct IAPContext*ctx,unsigned lingo,unsigned command,struct IAPSpan*request_span,struct IAPSpan*response_span){if(lingo==3){switch(command){'+body+'}}else{switch(command){'+ext+'}}return -99;}'
main=r"""
int main(void){
 struct IAPContext c={0};uint8_t buf[16];
 struct IAPGetTrackArtworkTimesPayload q={swap_32(1),swap_16(7),0,swap_16(1)};
 struct IAPSpan in={(void*)&q,sizeof q},out={buf,sizeof buf};
 assert(handle_command(&c,4,0x2a,&in,&out)==0x2b);assert(out.ptr-buf==4&&!memcmp(buf,"\0\0\0\0",4));
 q.track_index=swap_32(3);assert(handle_command(&c,4,0x2a,&in,&out)<0);q.track_index=0;
 q.format_id=swap_16(8);assert(handle_command(&c,4,0x2a,&in,&out)<0);q.format_id=swap_16(7);
 q.artwork_index=swap_16(1);assert(handle_command(&c,4,0x2a,&in,&out)<0);q.artwork_index=0;
 q.artwork_count=swap_16(2);assert(handle_command(&c,4,0x2a,&in,&out)<0);q.artwork_count=swap_16(1);
 art=false;assert(handle_command(&c,4,0x2a,&in,&out)<0);
 in.size=9;assert(handle_command(&c,4,0x2a,&in,&out)<0);
 puts("PASS: real artwork-time dispatch, zero offset, invalid track/format/index/count/missing art/truncation");
}
"""
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(pre+func+main)
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True)
 subprocess.run([str(p/'t')],check=True)
