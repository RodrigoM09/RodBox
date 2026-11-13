from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[2];s=(r/'firmware-source/firmware/drivers/usb-designware.c').read_text();a=s.index('static void usb_dw_log_iso_recovery(');b=s.index('/* A missed periodic IN',a)
pre=r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#define ISO_LOG_MAX 8
#define USB_LOG_ISO_STATE 1
#define USB_DIR_IN 128
static unsigned iso_probe_logged[4],logs;
static unsigned ctl=0x804480c0,ints=0x2010,DWC_DIEPMSK=0x201b,DWC_DAINTMSK=0xffff,DWC_DSTS=77u<<8,DWC_GINTSTS=0x1234;
#define DWC_DIEPCTL(e) ctl
#define DWC_DIEPINT(e) ints
static void usb_log(int type,int ep,int kind,unsigned c,unsigned d){
 assert(type==1&&ep==129);
 if(kind==8)assert(c==ctl&&d==ints);
 else if(kind==9)assert(c==DWC_DIEPMSK&&d==DWC_DAINTMSK);
 else {assert(kind==10&&c==77&&d==DWC_GINTSTS);}
 logs++;
}
'''
main=r'''
int main(void){
 for(unsigned i=0;i<100;i++)usb_dw_log_iso_recovery(1);
 assert(logs==24&&iso_probe_logged[1]==8);
 assert(ctl==0x804480c0&&ints==0x2010&&DWC_DIEPMSK==0x201b&&DWC_DAINTMSK==0xffff&&DWC_GINTSTS==0x1234);
 puts("PASS: production recovery snapshot captures raw endpoint/masks/frame; eight snapshot bound; no register writes");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(pre+s[a:b]+main)
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True);subprocess.run([str(p/'t')],check=True)
