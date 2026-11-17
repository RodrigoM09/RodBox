"""Actual USB callback and class reset with endpoint/queue ownership mocks.

No device access or controller emulation. --source accepts a prior version for
runtime regression reproduction; missing newly added helpers are harmless stubs.
"""
from pathlib import Path
import argparse
import importlib.util
import subprocess
import tempfile

root=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('extract',root/'tests/storage/test_usb_idle.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,default=root/'firmware-source/firmware/usbstack/usb_storage.c')
parser.add_argument('--scenario',choices=['all','cbw','reset','direction','time','csw'],default='all')
args=parser.parse_args();s=args.source.read_text()
types='\n'.join(s[s.index('struct '+n+' {'):s.index('} __attribute__ ((packed));',s.index('struct '+n+' {'))+len('} __attribute__ ((packed));')]
                for n in ['command_block_wrapper','command_status_wrapper'])
header=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#define MIN(a,b) ((a)<(b)?(a):(b))
#define CONFIG_RTC 1
#define USB_DIR_IN 128
#define USB_DIR_OUT 0
#define EP_IN 129
#define EP_OUT 1
#define WRITE_BUFFER_SIZE 4096
#define MAX_CBW_SIZE 512
#define UMS_STATUS_FAIL 1
#define UMS_STATUS_GOOD 0
#define SENSE_MEDIUM_ERROR 3
#define SENSE_ILLEGAL_REQUEST 5
#define ASC_WRITE_ERROR 12
#define ASC_READ_ERROR 17
#define ASC_INVALID_FIELD_IN_CBD 36
#define CBW_SIGNATURE 0x43425355
#define USB_BULK_GET_MAX_LUN 0xfe
#define USB_BULK_RESET_REQUEST 0xff
#define USB_CONTROL_ACK 0
#define HAVE_EXTENDED_MESSAGING_AND_NAME
#define CONFIG_USBOTG 1
#define USBOTG_DESIGNWARE 1
#define USBOTG_ARC 2
#define letoh32(a) (a)
#define logf(...) ((void)0)
#define IF_MD(...)
#define USBSTOR_WRITE_SECTORS_FILTER() 0
typedef uint64_t sector_t;
enum {WAITING_FOR_COMMAND,WAITING_FOR_RESET,WAITING_FOR_STORAGE,SENDING_BLOCKS,
 SENDING_RESULT,SENDING_FAILED_RESULT,RECEIVING_BLOCKS,RECEIVING_TIME,
 WAITING_FOR_CSW_COMPLETION_OR_COMMAND,WAITING_FOR_CSW_COMPLETION};
static int state;
static unsigned char cbw_buffer[MAX_CBW_SIZE],buffer[8192];
static struct {unsigned char *transfer_buffer;}tb={buffer};
static struct {unsigned block_size,count,data_residue,last_result,failed_write_residue;sector_t sector;int data_select,lun;void *data[2];uint32_t tag;}cur_cmd;
static struct {int sense_key,asc,ascq,information;}cur_sense_data;
static int commands,reads,writes,csws,csw_status,time_sets,stalls,receives,reset_stage,acks;
static bool in_pending,out_pending,queued_in,queued_out;
static void *out_buffer;
static void usb_drv_stall(int ep,bool stall,bool in){assert(stall && ep==(in?EP_IN:EP_OUT));stalls++;}
static void handle_scsi(struct command_block_wrapper *cbw){assert((void*)cbw==cbw_buffer);commands++;}
static void send_and_read_next(void){reads++;}
static void send_csw(int status){csws++;csw_status=status;state=WAITING_FOR_CSW_COMPLETION_OR_COMMAND;}
static int storage_write_sectors(sector_t sector,unsigned count,void *data){(void)sector;(void)count;(void)data;writes++;return 0;}
static void receive_block_data(void *data,int size){assert(data && size>0);state=RECEIVING_BLOCKS;}
static void set_day_of_week(struct tm *tm){(void)tm;}
static void set_time(struct tm *tm){(void)tm;time_sets++;}
static int storage_num_drives(void){return 1;}
static void usb_core_control_response(int status,void *p,int n){(void)p;(void)n;assert(status==USB_CONTROL_ACK);acks++;}
static void usb_drv_reset_endpoint(int ep,bool in){assert(ep==(in?EP_IN:EP_OUT));assert(reset_stage==(in?0:1));reset_stage++;if(in)in_pending=false;else out_pending=false;}
static void usb_core_clear_endpoint_completion(int ep){assert(reset_stage==(ep==EP_IN?2:3));reset_stage++;if(ep==EP_IN)queued_in=false;else queued_out=false;}
static int usb_drv_recv_nonblocking(int ep,void *p,int n){assert(ep==EP_OUT && p==cbw_buffer && n==MAX_CBW_SIZE);assert(!out_pending);if(reset_stage)assert(reset_stage==4 && !queued_in && !queued_out);out_pending=true;out_buffer=p;receives++;return 0;}
struct usb_ctrlrequest {unsigned char bRequest;};
'''
functions=[]
for name in ['require_reset_recovery','receive_cbw','account_data_transfer','yearday_to_daymonth','usb_storage_transfer_complete','usb_storage_control_request']:
    try:functions.append(m.extract(s,name))
    except ValueError:
        if name not in ['require_reset_recovery','receive_cbw']:raise
runner=r'''
static void setup(int new_state){
 memset(&cur_cmd,0,sizeof(cur_cmd));memset(&cur_sense_data,0,sizeof(cur_sense_data));
 memset(cbw_buffer,0,sizeof(cbw_buffer));memset(buffer,0xa5,sizeof(buffer));
 struct command_block_wrapper *cbw=(void*)cbw_buffer;
 cbw->signature=CBW_SIGNATURE;cbw->command_length=10;cbw->command_block[0]=0x28;cbw->flags=USB_DIR_IN;
 state=new_state;cur_cmd.block_size=512;cur_cmd.count=8;cur_cmd.data_residue=4096;
 cur_cmd.data[0]=buffer;cur_cmd.data[1]=buffer+4096;
 commands=reads=writes=csws=time_sets=stalls=receives=reset_stage=acks=0;
 in_pending=out_pending=queued_in=queued_out=false;out_buffer=NULL;
}
static void transfer(int dir,int status,int n){usb_storage_transfer_complete(1,dir,status,n);}
int main(int argc,char **argv){
 const char *scenario=argc>1?argv[1]:"all";bool all=!strcmp(scenario,"all");
 if(all || !strcmp(scenario,"cbw")){
  int lengths[]={-1,0,1,30,32,512};
  for(unsigned i=0;i<sizeof(lengths)/sizeof(lengths[0]);i++){
   setup(WAITING_FOR_COMMAND);transfer(USB_DIR_OUT,0,lengths[i]);
   assert(!commands && state==WAITING_FOR_RESET && stalls==2);
  }
  for(int bad=0;bad<6;bad++){
   setup(WAITING_FOR_COMMAND);struct command_block_wrapper *cbw=(void*)cbw_buffer;
   if(bad==0)cbw->signature=0;if(bad==1)cbw->flags=1;if(bad==2)cbw->lun=16;
   if(bad==3)cbw->command_length=0;if(bad==4)cbw->command_length=17;
   transfer(USB_DIR_OUT,bad==5?-1:0,31);
   assert(!commands && state==WAITING_FOR_RESET && stalls==2);
  }
  setup(WAITING_FOR_COMMAND);transfer(USB_DIR_OUT,0,31);assert(commands==1 && !stalls);
  setup(WAITING_FOR_CSW_COMPLETION_OR_COMMAND);transfer(USB_DIR_OUT,0,30);
  assert(!commands && state==WAITING_FOR_RESET && stalls==2);
  puts("PASS invalid CBW status, size, signature, flags, LUN bits and CDB length require reset; valid CBW works");
 }
 if(all || !strcmp(scenario,"direction")){
  int states[]={WAITING_FOR_COMMAND,WAITING_FOR_CSW_COMPLETION,SENDING_RESULT,SENDING_FAILED_RESULT,SENDING_BLOCKS,RECEIVING_BLOCKS,RECEIVING_TIME};
  for(unsigned i=0;i<sizeof(states)/sizeof(states[0]);i++){
   setup(states[i]);int dir=(state==WAITING_FOR_COMMAND || state==RECEIVING_BLOCKS || state==RECEIVING_TIME)?USB_DIR_IN:USB_DIR_OUT;
   transfer(dir,0,31);assert(!commands && !reads && !writes && !csws && !time_sets && !stalls && state==states[i]);
   assert(cur_cmd.data_residue==4096);
  }
  puts("PASS opposite-direction completions cannot dispatch stale commands/data or advance state");
 }
 if(all || !strcmp(scenario,"csw")){
  for(int order=0;order<2;order++){
   setup(WAITING_FOR_CSW_COMPLETION_OR_COMMAND);
   if(order)transfer(USB_DIR_OUT,0,31);
   transfer(USB_DIR_IN,0,sizeof(struct command_status_wrapper));
   if(!order)transfer(USB_DIR_OUT,0,31);
   assert(commands==1 && !stalls);
   setup(WAITING_FOR_CSW_COMPLETION_OR_COMMAND);transfer(USB_DIR_OUT,0,31);
   transfer(USB_DIR_IN,order?-1:0,order?sizeof(struct command_status_wrapper):0);
   assert(!commands && state==WAITING_FOR_RESET && stalls==2);
  }
  puts("PASS both command/CSW completion orders; failed CSW cannot execute next command");
 }
 if(all || !strcmp(scenario,"time")){
  for(int failure=0;failure<3;failure++){
   setup(RECEIVING_TIME);transfer(USB_DIR_OUT,failure==0?-1:0,failure==0?12:failure==1?0:11);
   assert(!time_sets && csws==1 && csw_status==UMS_STATUS_FAIL);
  }
  setup(RECEIVING_TIME);memset(buffer,0,12);buffer[0]=7;buffer[1]=234;
  transfer(USB_DIR_OUT,0,12);assert(time_sets==1 && csws==1 && csw_status==UMS_STATUS_GOOD);
  puts("PASS failed/truncated time payload cannot reuse old bytes; valid 12-byte time update works");
 }
 if(all || !strcmp(scenario,"reset")){
  for(int old_state=WAITING_FOR_COMMAND;old_state<=WAITING_FOR_CSW_COMPLETION;old_state++){
   setup(old_state);in_pending=out_pending=queued_in=queued_out=true;out_buffer=buffer;
   struct usb_ctrlrequest req={USB_BULK_RESET_REQUEST};uint8_t data[1];
   assert(usb_storage_control_request(&req,data,sizeof(data)));
   assert(reset_stage==4 && receives==1 && out_pending && out_buffer==cbw_buffer);
   assert(!in_pending && !queued_in && !queued_out && state==WAITING_FOR_COMMAND && acks==1 && !stalls);
   transfer(USB_DIR_OUT,0,31);assert(commands==1);
  }
  puts("PASS reset in every state cancels two endpoints, purges their events and rearms CBW in order");
 }
}
'''
with tempfile.TemporaryDirectory(prefix='rodbox-transport-') as t:
    p=Path(t);(p/'test.c').write_text(types+header+'\n'.join(functions)+runner)
    subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-function',
                    '-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test'),args.scenario],check=True)
