from pathlib import Path
import subprocess,tempfile,sys
r=Path(__file__).resolve().parents[2]
s=(Path(sys.argv[1]) if len(sys.argv)>1 else r/'firmware-source/firmware/drivers/usb-designware.c').read_text();a=s.index('static void usb_dw_epstart(');b=s.index('static int usb_dw_transfer(',a)
pre=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#define S5L8702 8702
#define USB_DIR_IN 128
#define CACHEALIGN_SIZE 32
#define logf(...) ((void)0)
#define usb_log(...) ((void)0)
#define MIN(a,b) ((a)<(b)?(a):(b))
#define PKTCNT(n) ((n)<<19)
#define MCCNT(n) ((n)<<29)
#define EPENA (1u<<31)
#define EPDIS (1u<<30)
#define SETD0PIDEF (1u<<28)
#define SETD1PIDOF (1u<<29)
#define CNAK (1u<<26)
#define NAKINTRPT (1u<<13)
#define ITTXFE (1u<<4)
#define EPTYP_ISOCHRONOUS 1
#define EPTYP_INTERRUPT 3
#define ISO_LOG_MAX 8
#define USB_DW_PHYSADDR(x) (x)
#define COMMIT_DCACHE_RANGE(p,n) ((void)0)
#define DISCARD_DCACHE_RANGE(p,n) ((void)0)
enum usb_dw_epdir{USB_DW_EPDIR_IN,USB_DW_EPDIR_OUT};
struct usb_dw_ep{uint32_t*addr;unsigned size,sizeleft;int status;bool busy;};
static struct usb_dw_ep eps[4][2];
static uint32_t ctl[4][2],tsiz[4][2],dma[4][2],ints[4],DWC_DSTS;
#define DWC_EPCTL(e,d) ctl[e][d]
#define DWC_DIEPCTL(e) ctl[e][0]
#define DWC_DIEPINT(e) ints[e]
#define DWC_EPTSIZ(e,d) tsiz[e][d]
#define DWC_EPDMA(e,d) dma[e][d]
static bool iso_synced[4],iso_waiting_token[4];static uint16_t iso_target_frame[4];
static unsigned iso_starts_logged[4][2];
static struct usb_dw_ep*usb_dw_get_ep(int e,int d){return &eps[e][d];}
static unsigned usb_dw_maxxfersize(int e,int d){(void)e;(void)d;return 4096;}
static unsigned usb_dw_maxpktsize(int e,int d){(void)e;(void)d;return 192;}
static unsigned usb_dw_calc_packets(unsigned n,unsigned m){return (n+m-1)/m;}
static unsigned usb_drv_get_frame_number(void){return (DWC_DSTS>>11)&0x7ff;}
static uint32_t pcm[48];
'''
main=r'''
int main(void){
 (void)ints;
 for(unsigned f=0;f<16384;f++){
  ctl[1][0]=(1u<<18)|EPDIS|SETD0PIDEF|SETD1PIDOF;iso_synced[1]=false;DWC_DSTS=f<<8;
  usb_dw_epstart(1,USB_DW_EPDIR_IN,pcm,192);
  assert(eps[1][0].busy&&eps[1][0].addr==pcm&&eps[1][0].size==192);
  assert(tsiz[1][0]==(PKTCNT(1)|MCCNT(1)|192));
#if CONFIG_CPU == S5L8702
  assert(!(ctl[1][0]&EPDIS));
  assert((ctl[1][0]&EPENA)&&!iso_waiting_token[1]&&iso_synced[1]);
  assert(iso_target_frame[1]==((f+1)&0x3fff));
  assert((ctl[1][0]&(SETD0PIDEF|SETD1PIDOF))==(((f+1)&1)?SETD1PIDOF:SETD0PIDEF));
#else
  assert(!(ctl[1][0]&EPENA)&&iso_waiting_token[1]&&!iso_synced[1]);
#endif
 }
 ctl[2][0]=2u<<18;usb_dw_epstart(2,USB_DW_EPDIR_IN,pcm,192);
 assert((ctl[2][0]&EPENA)&&!iso_synced[2]);
 puts("PASS: actual first-packet setup; all 14-bit phases/wrap, DMA size and buffer ownership, bulk exclusion, target isolation");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(pre+s[a:b]+main)
 for cpu in ['8702','0']:
  subprocess.run(['clang','-Wall','-Wextra','-Werror','-Wno-pointer-to-int-cast','-fsanitize=address,undefined','-DCONFIG_CPU='+cpu,str(p/'t.c'),'-o',str(p/'t')],check=True)
  subprocess.run([str(p/'t')],check=True)
