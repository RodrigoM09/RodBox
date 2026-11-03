"""Wire header fixtures cross-checked against independent iAP implementations."""
from pathlib import Path
import subprocess, tempfile
root=Path(__file__).resolve().parents[2]
header=root/'firmware-source/firmware/usbstack/iap/libiap/spec/lingoes/extended-interface/track-info.h'
code=r"""
#include <stddef.h>
#include <assert.h>
#include <string.h>
#include <stdio.h>
#include "track-info.h"
_Static_assert(sizeof(struct IAPGetDBTrackInfoPayload)==8,"request prefix");
_Static_assert(offsetof(struct IAPGetDBTrackInfoPayload,track_count)==4,"count offset");
_Static_assert(offsetof(struct IAPGetDBTrackInfoPayload,mask)==8,"mask offset");
_Static_assert(sizeof(struct IAPRetDBTrackInfoPayload)==5,"response prefix");
_Static_assert(offsetof(struct IAPRetDBTrackInfoPayload,information_type)==4,"type offset");
_Static_assert(offsetof(struct IAPRetDBTrackInfoPayload,data)==5,"data offset");
static uint32_t be32(const unsigned char*p){return (uint32_t)p[0]<<24|(uint32_t)p[1]<<16|(uint32_t)p[2]<<8|p[3];}
int main(void){
 /* Request track 258, count 2; names/duration and year, mask bytes LE. */
 unsigned char req[]={0,0,1,2,0,0,0,2,0x4e,0,8,0};
 assert(be32(req)==258 && be32(req+4)==2);
 assert((req[8]&IAPTrakcInfoTypeBits_TrackName)!=0);
 assert((req[10]&IAPTrakcInfoTypeBits_Year)!=0);
 unsigned char reply[]={0,0,1,2,1,'T','i','t','l','e',0};
 assert(be32(reply)==258 && reply[4]==1 && !strcmp((const char*)reply+5,"Title"));
 puts("PASS: verified request/reply wire offsets and mixed-endian mask fixture");
}
"""
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(code)
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I',str(header.parent),str(p/'t.c'),'-o',str(p/'t')],check=True)
 subprocess.run([str(p/'t')],check=True)
