"""Real generic-DAC initialization: choose supported nonpositive gain, read back."""
from pathlib import Path
import os,subprocess,tempfile
r=Path(__file__).resolve().parents[2]
s=Path(os.environ.get('RODBOX_HOST_AUDIO_SOURCE',str(r/'firmware-source/firmware/usbstack/usb_host_audio.c'))).read_text()
def fn(name):
 a=s.index('static '+('bool ' if name=='dac_safe_volume' else 'void ')+name+'(');b=s.index('{',a);depth=1;e=b+1
 while depth:depth+=(s[e]=='{')-(s[e]=='}');e+=1
 return s[a:e]+'\n'
pre=r'''
#include <stdint.h>
#include <stdbool.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
#define USB_DIR_IN 0x80
#define USB_DIR_OUT 0
#define USB_TYPE_CLASS 0x20
#define USB_RECIP_INTERFACE 1
#define UAC1_GET_CUR 0x81
#define UAC1_GET_MIN 0x82
#define UAC1_GET_MAX 0x83
#define UAC1_GET_RES 0x84
#define UAC2_CUR 1
#define UAC2_RANGE 2
#define UAC1_FU_MUTE 1
#define UAC1_FU_VOLUME 2
#define USB_LOG_HOST_ENUM 0
#define MIN(a,b) ((a)<(b)?(a):(b))
static void usb_log(int kind,int ok,int channel,uintptr_t name,int value){(void)kind;(void)ok;(void)channel;(void)name;(void)value;}
static int dev_addr=1,fu_unit=2;
static uint8_t fu_ctl[3];
static struct{int ac_iface,uac;}status={0,1};
static int low,high,step,subranges,fail_request,applied[3],sets[3],reads[3];
static int usb_drv_host_last_status(void){return 0;}
static void put(uint8_t*b,int v){b[0]=(unsigned)v&255;b[1]=((unsigned)v>>8)&255;}
static int usb_drv_host_control(int addr,int type,int req,int value,int index,uint8_t*b,int len){
 assert(addr==dev_addr&&index==(fu_unit<<8));int channel=value&255;
 if((value>>8)==UAC1_FU_MUTE)return len;
 assert((value>>8)==UAC1_FU_VOLUME);
 if(req==fail_request)return -1;
 if(!(type&USB_DIR_IN)){assert(len==2);applied[channel]=(int16_t)(b[0]|b[1]<<8);sets[channel]++;return 2;}
 if(req==UAC1_GET_MIN){put(b,low);return 2;}
 if(req==UAC1_GET_MAX){put(b,high);return 2;}
 if(req==UAC1_GET_RES){put(b,step);return 2;}
 if(req==UAC2_RANGE){assert(len==8);put(b,subranges);put(b+2,low);put(b+4,high);put(b+6,step);return 8;}
 if(req==UAC1_GET_CUR||req==UAC2_CUR){reads[channel]++;put(b,applied[channel]);return 2;}
 assert(0);return -1;
}
'''
main=r'''
static void scenario(int uac,int lo,int hi,int res,int expect){
 status.uac=uac;low=lo;high=hi;step=res;subranges=1;fail_request=0;
 memset(fu_ctl,0,sizeof fu_ctl);fu_ctl[0]=3;
 memset(sets,0,sizeof sets);memset(reads,0,sizeof reads);dac_unmute();
 assert(sets[0]==1&&applied[0]==expect&&applied[0]<=0 && "automatic DAC gain must not exceed supported unity");
 assert(reads[0]==1 && "gain change must be read back");assert(!sets[1]&&!sets[2]);
}
int main(void){
 for(int uac=1;uac<=2;uac++){
  scenario(uac,-60*256,12*256,128,0);
  scenario(uac,-60*256,-6*256,128,-6*256);
  scenario(uac,-3*256,4*256,2*256,-256); /* unity is between grid points */
  scenario(uac,-60*256,12*256,0,0);
  scenario(uac,-32768,32767,1,0);
  low=256;high=12*256;step=256;memset(sets,0,sizeof sets);dac_unmute();assert(!sets[0]);
  low=1024;high=-1024;memset(sets,0,sizeof sets);dac_unmute();assert(!sets[0]);
 }
 scenario(1,-60*256,12*256,128,0);
 for(int req=UAC1_GET_MIN;req<=UAC1_GET_RES;req++){
  fail_request=req;memset(sets,0,sizeof sets);dac_unmute();assert(!sets[0]);
 }
 fail_request=0;status.uac=2;subranges=2;memset(sets,0,sizeof sets);dac_unmute();assert(!sets[0]);
 subranges=1;fail_request=UAC2_RANGE;dac_unmute();assert(!sets[0]);
 fail_request=0;status.uac=1;memset(fu_ctl,0,sizeof fu_ctl);fu_ctl[0]=1;fu_ctl[1]=fu_ctl[2]=2;
 memset(sets,0,sizeof sets);memset(reads,0,sizeof reads);dac_unmute();assert(!sets[0]&&sets[1]==1&&sets[2]==1&&reads[1]==1&&reads[2]==1);
 fu_unit=0;memset(sets,0,sizeof sets);dac_unmute();assert(!sets[0]&&!sets[1]&&!sets[2]);
 puts("PASS: actual UAC1/UAC2 DAC init chooses supported unity-or-lower grid gain with readback; negative maxima, positive-only/malformed/multi-range/failed reads, per-channel and absent feature unit covered");
}
'''
code=pre+(fn('dac_safe_volume') if 'static bool dac_safe_volume(' in s else '')+fn('dac_unmute')+main
with tempfile.TemporaryDirectory(prefix='pb56-dacgain-') as d:
 p=Path(d);(p/'t.c').write_text(code)
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True)
 subprocess.run([str(p/'t')],check=True)
