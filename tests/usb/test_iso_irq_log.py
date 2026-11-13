from pathlib import Path
import subprocess,tempfile,sys
r=Path(__file__).resolve().parents[2];s=(Path(sys.argv[1]) if len(sys.argv)>1 else r/'firmware-source/firmware/drivers/usb-designware.c').read_text();a=s.index('static void usb_dw_log_iso_irq(');b=s.index('static void usb_dw_iepint(',a)
pre=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#define USB_DW_EPDIR_IN 1
#define USB_DIR_IN 128
#define EPTYP_ISOCHRONOUS 1
#define EPDISD 2
#define TXFE 128
#define INEPNE 64
#define NAKINTRPT (1u<<13)
#define ITTXFE (1u<<4)
#define ISO_LOG_MAX 8
#define USB_LOG_ISO_STATE 1
static unsigned ctl[4],DWC_DSTS=123u<<8,count,last_flags;
static uint8_t iso_irq_logged[4],iso_token_irq_logged[4];
#define DWC_DIEPCTL(ep) ctl[ep]
struct ep {bool active;};static struct ep eps[4];
static struct ep* usb_dw_get_ep(int e,int d){assert(d==1);return &eps[e];}
static void usb_log(int type,int ep,int kind,unsigned flags,unsigned frame){assert(type==1&&ep==129&&(kind==6||kind==7)&&frame==123);count++;last_flags=flags;}
'''
main=r'''
int main(void){
 eps[1].active=true;ctl[1]=1u<<18;
 for(unsigned i=0;i<100;i++)usb_dw_log_iso_irq(1,EPDISD|TXFE|INEPNE);
 assert(count==0);
 usb_dw_log_iso_irq(1,1u<<13);assert(count==1&&last_flags==(1u<<13));
 for(unsigned i=0;i<100;i++)usb_dw_log_iso_irq(1,1);
 assert(count==9);
 for(unsigned i=0;i<100;i++)usb_dw_log_iso_irq(1,ITTXFE|INEPNE);
 assert(count==16);
 eps[2].active=true;ctl[2]=2u<<18;usb_dw_log_iso_irq(2,1);
 usb_dw_log_iso_irq(0,1);eps[3].active=false;ctl[3]=1u<<18;usb_dw_log_iso_irq(3,1);
 assert(count==16&&ctl[1]==(1u<<18));
 puts("PASS: actual ISO IRQ logger bound, token/complete flags, software/FIFO-only suppression, bulk/control/inactive exclusion, no register mutation");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(pre+s[a:b]+main)
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True);subprocess.run([str(p/'t')],check=True)
