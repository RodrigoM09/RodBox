"""Exercise the production non-native batch pump, including PB36 failure flood."""
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[2]
s=(r/'firmware-source/firmware/usbstack/usb_core.c').read_text()
a=s.index('static uint8_t batch_ep = 0;')
b=s.index('\n#endif',a)
pre=r"""
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <assert.h>
#include <stdio.h>
#define logf(...) ((void)0)
#define EP_NUM(n) ((n)&15)
typedef void(*usb_drv_batch_get_more)(const void**,size_t*);
int usb_drv_batch_stop(void);
static unsigned pulls,sends,resets;
static bool hw_busy;
static void usb_drv_reset_endpoint(int ep,bool send);
static int submit_status;
static size_t source_length=176;
static uint8_t pcm[192];
static void source(const void**p,size_t*n){pulls++;*p=pcm;*n=source_length;}
static int usb_drv_send_nonblocking(int ep,void*p,size_t n){assert(ep==1&&p==pcm&&n==source_length);sends++;if(hw_busy)return -1;hw_busy=submit_status==0;return submit_status;}
static int disable_irq_save(void){return 0;}
static void restore_irq(int n){(void)n;}
"""
main=r"""
int main(void){
 assert(!usb_drv_batch_init(0x81,source));
 assert(usb_drv_batch_init(0x82,source)==-1);
 assert(!usb_drv_batch_start());assert(pulls==1&&sends==1);
 assert(!usb_drv_batch_start());assert(pulls==1); /* idempotent */
 for(int n=0;n<10;n++)batch_xfer_complete(0,176);
 assert(pulls==11&&sends==11);
 batch_xfer_complete(-1,0);
 for(int n=0;n<40571;n++)batch_xfer_complete(-1,0);
 assert(pulls==11&&sends==11&&batch_stopped&&batch_failed==1);
 batch_xfer_complete(0,176);assert(pulls==11); /* stale event after stop */
 assert(!usb_drv_batch_start());assert(pulls==12);
 batch_xfer_complete(0,100);assert(pulls==12&&batch_stopped); /* short success */
 assert(!usb_drv_batch_start());batch_xfer_complete(0,-1);assert(batch_stopped);
 assert(!usb_drv_batch_start());batch_xfer_complete(0,192);assert(batch_stopped);
 unsigned before=pulls;assert(!usb_drv_batch_stop());batch_get_and_send();assert(pulls==before);
 submit_status=-1;assert(usb_drv_batch_start()==-1&&batch_stopped);
 before=pulls;batch_xfer_complete(-1,0);assert(pulls==before);
 submit_status=0;source_length=0;assert(!usb_drv_batch_start()&&batch_stopped);
 uint32_t empty,failed;usb_drv_batch_take_counts(&empty,&failed);
 assert(empty==0&&failed==5);usb_drv_batch_take_counts(&empty,&failed);assert(failed==0);
 assert(!usb_drv_batch_deinit()&&!batch_ep);
 source_length=176;assert(!usb_drv_batch_init(0x81,source));assert(!usb_drv_batch_start());
 unsigned p=pulls;
 for(int n=0;n<50;n++){
  assert(hw_busy);assert(!usb_drv_batch_stop()&&!hw_busy);
  assert(!usb_drv_batch_start()&&hw_busy);
 }
 assert(pulls==p+50&&resets>=50);
 assert(!usb_drv_batch_deinit());assert(usb_drv_batch_start()==-1);
 puts("PASS: production batch pump: 40,571 failures consume no new PCM; normal completions, short/error submissions, restart/stop/deinit");
}
"""
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(pre+s[a:b].replace('static void batch_xfer_complete(', 'static void production_batch_xfer_complete(')+r"""
static void usb_drv_reset_endpoint(int ep,bool send){assert(ep==1&&send&&batch_stopped);hw_busy=false;resets++;}
static void batch_xfer_complete(int status,int n){hw_busy=false;production_batch_xfer_complete(status,n);}
"""+main)
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True)
 subprocess.run([str(p/'t')],check=True)
