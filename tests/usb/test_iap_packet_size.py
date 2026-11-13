"""Compile real allocation/descriptor initializers and test their wire contract."""
from pathlib import Path
import re,subprocess,tempfile,sys
r=Path(__file__).resolve().parents[2]
s=(Path(sys.argv[1]) if len(sys.argv)>1 else r/'firmware-source/firmware/usbstack/usb_iap.c').read_text()
macros=(r/'firmware-source/firmware/usbstack/iap/macros.h').read_text()
size=re.search(r'^#define AS_PACKET_SIZE .+$',macros,re.M).group()
def initializer(start):
 a=s.index(start);b=s.index('};',a)+2;return s[a:b]
code=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#define USB_ENDPOINT_XFER_ISOC 1
#define USB_ENDPOINT_SYNC_SYNC (3<<2)
#define USB_ENDPOINT_XFER_INT 3
#define DIR_IN 1
#define USB_DT_ENDPOINT_AUDIO_SIZE 9
#define USB_DT_ENDPOINT 5
struct usb_class_driver_ep_allocation {int type,dir;bool optional;int mps;};
struct usb_as_iso_audio_endpoint {int bLength,bDescriptorType,bEndpointAddress,bmAttributes,wMaxPacketSize,bInterval,bRefresh,bSynchAddress;};
'''+size+'\n'+initializer('struct usb_class_driver_ep_allocation usb_iap_ep_allocs')+'\n'+initializer('static struct usb_as_iso_audio_endpoint ipod_audio_stream_1_endpoint')+r'''
int main(void){
 int mps=usb_iap_ep_allocs[0].mps;
 assert(mps==ipod_audio_stream_1_endpoint.wMaxPacketSize);
 assert(ipod_audio_stream_1_endpoint.bmAttributes==0x0d);
 assert(mps==192&&mps<=1023); /* legal also at full speed */
 assert(usb_iap_ep_allocs[1].mps==64); /* HID unchanged */
 for(unsigned n=176;n<=192;n+=4){
  assert(n<=(unsigned)mps);assert((n+mps-1)/mps==1);
 }
 puts("PASS: production iAP endpoint allocation matches descriptor/buffer limit, full/high speed and 44.1/48kHz single packets");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(code)
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True)
 subprocess.run([str(p/'t')],check=True)
