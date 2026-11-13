from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[2]
s=(r/'firmware-source/firmware/drivers/usb-designware.c').read_text()
a=s.index('static bool usb_dw_iso_token(');b=s.index('static void usb_dw_iepint(',a)
dispatch=s[s.index('    uint32_t epints = DWC_DIEPINT(ep);', b):s.index('    if ((epints & EPDISD)', b)]
pre=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#define USB_DW_EPDIR_IN 1
#define USB_DIR_IN 128
#define USB_LOG_ISO_STATE 0
#define usb_log(...) ((void)0)
#define EPENA (1u<<31)
#define EPTYP_ISOCHRONOUS 1
#define NAKINTRPT (1u<<13)
#define ITTXFE (1u<<4)
static unsigned ints[4],tail;
#define DWC_DIEPINT(e) ints[e]
static unsigned ctl[4],DWC_DSTS,starts;static int hs=1;
#define DWC_DIEPCTL(e) ctl[e]
static bool iso_waiting_token[4],iso_synced[4];static uint16_t iso_target_frame[4];
struct usb_dw_ep {bool active,busy;void*req_addr;unsigned req_size;};
static struct usb_dw_ep eps[4];
static struct usb_dw_ep*usb_dw_get_ep(int ep,int dir){assert(dir==1);return &eps[ep];}
static int usb_drv_port_speed(void){return hs;}
static void usb_dw_epstart(int ep,int dir,void*p,unsigned n){assert(ep==1&&dir==1&&p==eps[1].req_addr&&n==192);starts++;}
int buffer;
'''
main=r'''
int main(void){
 eps[1]=(struct usb_dw_ep){true,true,&buffer,192};ctl[1]=1u<<18;
 for(unsigned frame=0;frame<16384;frame++){
  iso_waiting_token[1]=true;DWC_DSTS=frame<<8;
  assert(usb_dw_iso_token(1));assert(iso_synced[1]&&!iso_waiting_token[1]);
  assert(iso_target_frame[1]==((frame+8)&0x3fff));
  unsigned prev=starts;assert(!usb_dw_iso_token(1)&&starts==prev);
 }
 for(unsigned event=0;event<3;event++){
  unsigned flags[]={NAKINTRPT,ITTXFE,NAKINTRPT|ITTXFE};
  iso_waiting_token[1]=true;ints[1]=flags[event]|1;unsigned prev=starts;
  dispatch_irq(1);assert(starts==prev+1&&tail==0);
 }
 hs=0;iso_waiting_token[1]=true;assert(usb_dw_iso_token(1)&&iso_target_frame[1]==0);
 iso_waiting_token[1]=true;ctl[1]|=EPENA;assert(!usb_dw_iso_token(1));
 ctl[1]=2u<<18;assert(!usb_dw_iso_token(1));ctl[1]=1u<<18;
 eps[1].busy=false;assert(!usb_dw_iso_token(1));eps[1].busy=true;
 eps[1].active=false;assert(!usb_dw_iso_token(1));assert(!usb_dw_iso_token(0));
 puts("PASS: host token synchronization, all HS phases/wrap, FS cadence, same-buffer ownership, duplicate/bulk/inactive guards");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(pre+s[a:b]+'static void dispatch_irq(int ep){'+dispatch+'tail++;}'+main)
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True)
 subprocess.run([str(p/'t')],check=True)
