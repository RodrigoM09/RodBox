from pathlib import Path
import subprocess,tempfile,sys
r=Path(__file__).resolve().parents[2];s=(Path(sys.argv[1]) if len(sys.argv)>1 else r/'firmware-source/firmware/drivers/usb-designware.c').read_text();a=s.index('void usb_drv_reset_endpoint(');b=s.index('bool usb_drv_stalled(',a)
pre=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#define EP_NUM(e) ((e)&15)
#define EPTYP_ISOCHRONOUS 1
enum usb_dw_epdir{USB_DW_EPDIR_IN,USB_DW_EPDIR_OUT};
static struct ep{bool active,busy;} eps[4][2];
static bool iso_recovering[4],iso_synced[4],iso_waiting_token[4],iso_prime_complete[4];
static unsigned iso_prime_retries[4],iso_target_frame[4],iso_irq_logged[4],iso_token_irq_logged[4];
static unsigned ctl[4],irq,flushes;
#define DWC_DIEPCTL(e) ctl[e]
static struct ep* usb_dw_get_ep(int e,int d){return &eps[e][d];}
static void usb_dw_target_disable_irq(void){assert(!irq);irq=1;}
static void usb_dw_target_enable_irq(void){assert(irq);irq=0;}
static void usb_dw_flush_endpoint(int e,int d){assert(irq&&eps[e][d].busy);eps[e][d].busy=false;flushes++;}
static void exhausted(void){iso_prime_retries[1]=8;iso_prime_complete[1]=true;iso_synced[1]=true;iso_recovering[1]=true;iso_waiting_token[1]=true;iso_target_frame[1]=99;iso_irq_logged[1]=8;iso_token_irq_logged[1]=8;}
'''
main=r'''
int main(void){
 ctl[1]=1u<<18;eps[1][0].active=true;
 for(unsigned busy=0;busy<2;busy++){
  exhausted();eps[1][0].busy=busy;usb_drv_reset_endpoint(0x81,true);
  assert(!iso_prime_retries[1]&&!iso_prime_complete[1]&&!iso_synced[1]&&!iso_recovering[1]&&!iso_waiting_token[1]);
  assert(!iso_target_frame[1]&&!iso_irq_logged[1]&&!iso_token_irq_logged[1]&&!irq);
  assert(flushes==busy&&ctl[1]==(1u<<18));
 }
 exhausted();ctl[1]=2u<<18;usb_drv_reset_endpoint(0x81,true);assert(iso_prime_retries[1]==8);
 ctl[1]=1u<<18;usb_drv_reset_endpoint(1,false);assert(iso_prime_retries[1]==8);
 eps[1][0].active=false;usb_drv_reset_endpoint(0x81,true);assert(iso_prime_retries[1]==8);
 puts("PASS: actual reset clears exhausted idle/busy ISO state, no idle flush/completion; bulk/OUT/inactive excluded");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(pre+s[a:b]+main)
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True);subprocess.run([str(p/'t')],check=True)
