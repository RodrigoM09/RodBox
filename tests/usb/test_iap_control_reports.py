"""Actual control buffer and GET_REPORT zero-response helper; no device I/O."""
from pathlib import Path
import re,subprocess,tempfile
r=Path(__file__).resolve().parents[2]/'firmware-source/firmware/usbstack'
s=(r/'usb_core.c').read_text();a=s.index('#ifdef USB_ENABLE_IAP\n/* iAP high-speed HID');b=s.index('\n#endif',a)+len('\n#endif');decl=s[a:b]
s=(r/'usb_iap.c').read_text();a=s.index('static void respond_zero(');b=s.index('\nstatic bool control_request_if_std',a);func=s[a:b]
pre='''#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#define USB_DEVBSS_ATTR
#define ERROR(...) ((void)0)
#define USB_CONTROL_STALL 0
#define USB_CONTROL_ACK 1
struct usb_ctrlrequest {unsigned wLength;};
static int result;static size_t length;
static void usb_core_control_response(int r,void *p,size_t n){(void)p;result=r;length=n;}
'''
main='''
int main(void){
#ifdef USB_ENABLE_IAP
 unsigned sizes[]={6,10,14,18,26,50,96,194,258,386,514,768};
 for(unsigned i=0;i<sizeof(sizes)/sizeof(*sizes);i++){
  memset(usb_control_data,0xa5,sizeof usb_control_data);
  struct usb_ctrlrequest q={sizes[i]};respond_zero(&q,usb_control_data,sizeof usb_control_data);
  assert(result==USB_CONTROL_ACK && length==sizes[i]);
  for(unsigned j=0;j<sizes[i];j++)assert(usb_control_data[j]==0);
  for(unsigned j=sizes[i];j<sizeof usb_control_data;j++)assert(usb_control_data[j]==0xa5);
 }
#else
 assert(sizeof usb_control_data==256);
#endif
 struct usb_ctrlrequest q={sizeof usb_control_data+1};
 respond_zero(&q,usb_control_data,sizeof usb_control_data);assert(result==USB_CONTROL_STALL && length==0);
 puts("PASS: advertised iAP control report sizes and oversized request bounds");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(pre+decl+'\n'+func+main)
 for flags in [[],['-DUSB_ENABLE_IAP']]:
  subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',*flags,str(p/'t.c'),'-o',str(p/'t')],check=True)
  subprocess.run([str(p/'t')],check=True)
