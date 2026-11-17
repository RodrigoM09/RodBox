from pathlib import Path
import subprocess,tempfile,sys
r=Path(__file__).resolve().parents[2]
s=(Path(sys.argv[1]) if len(sys.argv)>1 else r/'firmware-source/firmware/drivers/usb-designware.c').read_text()
a=s.index('static void usb_dw_incomplete_iso_in(');b=s.index('static void usb_dw_iepint(',a)
helper=s[a:s.index('static bool usb_dw_iso_token(',a)]
a=s.index('    if ((epints & EPDISD) && iso_recovering[ep])',b);b=s.index('    if (epints & TOC)',a)
finish=s[a:b]
pre=r"""
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#define USB_NUM_ENDPOINTS 4
#define S5L8702 8702
#define CONFIG_CPU S5L8702
#define USB_DW_EPDIR_IN 1
#define USB_DIR_IN 128
#define EPTYP_ISOCHRONOUS 1
#define EPENA (1u<<31)
#define EPDIS (1u<<30)
#define SNAK (1u<<27)
#define XFRC 1
#define EPDISD 2
#define TOC 8
#define AHBERR 4
#define IISOIXFR (1u<<20)
#define TXFFLSH 1
#define USB_LOG_ISO_ERROR 0
#define ISO_LOG_MAX 8
static unsigned iso_errors_logged[4][2];
#define USB_LOG_ISO_STATE 1
static unsigned retry_logs, incomplete_logs;
#define usb_log(t,e,b,c,d) do { if ((t)==1 && (b)==4) retry_logs++; if ((t)==1 && (b)==5) incomplete_logs++; } while(0)
#define usb_dw_log_iso_recovery(ep) ((void)0)
static unsigned regs_ctl[4],ints[4],DWC_GINTSTS,DWC_DSTS,DWC_DAINTMSK=15;
static uint16_t iso_target_frame[4];
static unsigned char iso_prime_retries[4];
static bool iso_prime_complete[4];
static unsigned sizes[4],rearms;
static bool highspeed=true;
static int usb_drv_port_speed(void){return highspeed;}
#define DWC_EPTSIZ(e,d) sizes[e]
#define DWC_DIEPCTL(e) regs_ctl[e]
#define DWC_DIEPINT(e) ints[e]
#define GET_DTXFNUM(e) (e)
struct usb_dw_ep{bool active,busy;int status,complete;void *req_addr;unsigned req_size;};
static struct usb_dw_ep endpoints[4];
static bool iso_recovering[4],iso_synced[4],iso_waiting_token[4];
static unsigned flushed,released,completed,last_ep;
static struct usb_dw_ep* usb_dw_get_ep(int ep,int dir){assert(dir==1);return &endpoints[ep];}

static unsigned usb_dw_maxpktsize(int ep,int dir){(void)ep;(void)dir;return 192;}
static void usb_dw_epstart(int e,int dir,void *buf,unsigned size){assert(dir==1&&buf==endpoints[e].req_addr&&size==endpoints[e].req_size);rearms++;}
static void usb_dw_flush_fifo(int f,int ep){assert(f==TXFFLSH);flushed++;last_ep=ep;}
static void semaphore_release(int*p){(void)p;released++;}
static void complete_transfer(int ep,int dir,int status,int n){assert(dir==128&&status==-1&&n==0);assert(!endpoints[ep].busy);completed++;}
"""
main=r"""
int main(void){
 (void)usb_drv_port_speed;
 for(int e=0;e<4;e++){endpoints[e]=(struct usb_dw_ep){true,true,0,0,0,192};regs_ctl[e]=EPENA|(1u<<18);}
 sizes[1]=0; /* packet count zero: never replay */
 regs_ctl[2]=EPENA|(2u<<18); /* storage/bulk */
 ints[3]=XFRC; /* finished packet must not be cancelled */
 iso_prime_complete[1]=true;
 iso_synced[1]=true;iso_target_frame[1]=108;DWC_DSTS=102u<<8;
 usb_dw_incomplete_iso_in();assert(!iso_recovering[1]); /* future HS interval */
 iso_target_frame[1]=2;DWC_DSTS=16382u<<8;
 usb_dw_incomplete_iso_in();assert(!iso_recovering[1]); /* future after wrap */
 iso_target_frame[1]=16382;DWC_DSTS=2u<<8;
 usb_dw_incomplete_iso_in();
 assert(!iso_recovering[0]&&iso_recovering[1]&&!iso_recovering[2]&&!iso_recovering[3]);
 assert((regs_ctl[1]&(EPDIS|SNAK))==(EPDIS|SNAK));assert(!completed&&!flushed);
 finish(1,0);assert(!completed);
 finish(1,EPDISD|XFRC);assert(completed==1&&flushed==1&&released==1&&last_ep==1&&!iso_synced[1]&&!iso_waiting_token[1]);
 finish(1,EPDISD);assert(completed==1); /* no duplicate callback */
 endpoints[1].busy=true;DWC_DAINTMSK=0;usb_dw_incomplete_iso_in();assert(!iso_recovering[1]);
 DWC_DAINTMSK=15;endpoints[1].active=false;usb_dw_incomplete_iso_in();assert(!iso_recovering[1]);
 endpoints[1].active=true;
 for(int n=0;n<100;n++){
  endpoints[1].busy=true;regs_ctl[1]=EPENA|(1u<<18);
  usb_dw_incomplete_iso_in();finish(1,EPDISD);
 }
 assert(iso_errors_logged[1][1]==ISO_LOG_MAX);
 /* Host startup may exceed eight attempts. Retain the same packet for
    10000 service windows without completion, new PCM or counter wrap. */
 iso_prime_complete[1]=false;iso_prime_retries[1]=0;sizes[1]=1u<<19;
 unsigned before=completed, releases=released;
 retry_logs=incomplete_logs=0;
 for(unsigned n=0;n<10000;n++){
  endpoints[1].busy=true;iso_recovering[1]=true;iso_synced[1]=true;
  unsigned parity=iso_target_frame[1]&1;
  finish(1,EPDISD);
  assert(endpoints[1].busy&&completed==before&&released==releases);
  assert((iso_target_frame[1]&1)!=parity);
  assert(iso_prime_retries[1]<=ISO_LOG_MAX);
 }
 assert(rearms==10000&&iso_prime_retries[1]==ISO_LOG_MAX);
 assert(retry_logs==ISO_LOG_MAX&&incomplete_logs==ISO_LOG_MAX);
 /* Stop, hardware faults, delivered packets and established-stream loss
    must not enter the startup retry path. */
 for(unsigned mode=0;mode<5;mode++){
  endpoints[1].active=mode!=0;endpoints[1].busy=true;
  iso_prime_complete[1]=mode==1;iso_recovering[1]=true;
  sizes[1]=mode==2?0:1u<<19;
  finish(1,EPDISD|(mode==3?TOC:mode==4?AHBERR:0));
  assert(rearms==10000&&completed==before+mode+1);
 }
 endpoints[1].active=true;
 /* Unknown HS phase must survive every early microframe, including wrap.
    Same endpoint remains armed until the entire advertised interval elapses. */
 iso_prime_complete[1]=false;iso_synced[1]=true;ints[1]=0;
 for(unsigned f=0;f<16384;f++){
  iso_recovering[1]=false;endpoints[1].busy=true;regs_ctl[1]=EPENA|(1u<<18);
  iso_target_frame[1]=(f+1)&0x3fff;
  for(unsigned k=0;k<8;k++){
   DWC_DSTS=((f+k)&0x3fff)<<8;usb_dw_incomplete_iso_in();
   assert(!iso_recovering[1]&&!(regs_ctl[1]&EPDIS));
  }
  DWC_DSTS=((f+8)&0x3fff)<<8;usb_dw_incomplete_iso_in();assert(iso_recovering[1]);
 }
 /* Full-speed one-frame scheduling and established HS streams unchanged. */
 for(unsigned mode=0;mode<2;mode++){
  highspeed=mode;iso_prime_complete[1]=mode;iso_recovering[1]=false;
  regs_ctl[1]=EPENA|(1u<<18);iso_target_frame[1]=8;DWC_DSTS=8<<8;
  usb_dw_incomplete_iso_in();assert(iso_recovering[1]);
 }
 puts("PASS: production ISO recovery selection, deferred completion, bulk/control exclusion, stale/duplicate events");
}
"""
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(pre+helper+'\nstatic void finish(int ep,unsigned epints){'+finish+'}\n'+main)
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True)
 subprocess.run([str(p/'t')],check=True)
