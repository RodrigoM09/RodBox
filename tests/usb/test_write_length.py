"""Extract current staged RECEIVING_BLOCKS arm and actual CSW/residue helpers.
Mocks only hardware I/O; ASan/UBSan checks host control flow, not USB hardware.
"""
from pathlib import Path
import re, subprocess,tempfile,sys
base=Path(__file__).resolve().parent
s=Path(sys.argv[1]).read_text() if len(sys.argv)>1 else (base.parents[1]/'firmware-source/firmware/usbstack/usb_storage.c').read_text()
def function(name):
    m=re.search(r'^static void '+name+r'\([^;]*?\)\s*\{',s,re.M)
    assert m,name
    start=s.index('{',m.start()); i=start+1; depth=1
    while depth:
        depth+=(s[i]=='{')-(s[i]=='}'); i+=1
    return s[m.start():i]
arm=s[s.index('        case RECEIVING_BLOCKS:',s.index('static void usb_storage_transfer_complete(int ep,int dir,int status,int length)\n{')):]
recovery=arm[arm.index('        case WAITING_FOR_CSW_COMPLETION_OR_COMMAND:'):arm.index('        case SENDING_RESULT:')]
arm=arm[:arm.index('        case WAITING_FOR_CSW_COMPLETION_OR_COMMAND:')]
header=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define MIN(a,b) ((a)<(b)?(a):(b))
#define WRITE_BUFFER_SIZE 4096
#define CONFIG_RTC 0
#define USB_DIR_IN 128
#define USB_DIR_OUT 0
#define EP_IN 129
#define EP_OUT 1
#define MAX_CBW_SIZE 31
#define UMS_STATUS_FAIL 1
#define UMS_STATUS_GOOD 0
#define SENSE_MEDIUM_ERROR 3
#define ASC_WRITE_ERROR 12
#define CSW_SIGNATURE 0x53425355
#define htole32(a) (a)
#define logf(...) ((void)0)
#define IF_MD(...)
#define USBSTOR_WRITE_SECTORS_FILTER() 0
#define WAITING_FOR_COMMAND 0
#define RECEIVING_BLOCKS 1
#define WAITING_FOR_CSW_COMPLETION_OR_COMMAND 2
#define SENDING_RESULT 3
#define SENDING_FAILED_RESULT 4
#define SENDING_BLOCKS 5
#define WAITING_FOR_CSW_COMPLETION 6
struct command_block_wrapper { int unused; };
static int state;
typedef uint64_t sector_t;
struct command_status_wrapper {uint32_t signature,tag,data_residue;uint8_t status;};
static struct command_status_wrapper csw;
static struct {struct command_status_wrapper *csw;} tb={&csw};
static char cbw_buffer[31], data0[4096],data1[4096];
static struct {unsigned block_size,count,data_residue;sector_t sector;int data_select,lun;void *data[2];uint32_t tag;}cur_cmd;
static struct {int sense_key,asc,ascq,information;}cur_sense_data;
static int commands;
static void handle_scsi(struct command_block_wrapper *cbw){assert((void*)cbw==cbw_buffer);commands++;}
static int writes,sends,recvs; static unsigned written_count;static sector_t written_sector;static void *written_data;
static void *last_recv;static int last_recv_size;
static int usb_drv_send_nonblocking(int ep,void *p,int n){assert(ep==EP_IN && p==tb.csw && n==sizeof(csw)); sends++;return 0;}
static int usb_drv_recv_nonblocking(int ep,void *p,int n){assert(ep==EP_OUT);recvs++;last_recv=p;last_recv_size=n;return 0;}
static int storage_write_sectors(sector_t sector,unsigned count,void *data){writes++;written_count=count;written_sector=sector;written_data=data;return 0;}
'''
runner=r'''
static void transfer(int dir,int status,int length) {
 struct command_block_wrapper *cbw=(void*)cbw_buffer;
 account_data_transfer(dir,status,length);
 switch(state) {
''' + arm + recovery + r'''
 default: break;
 }
}
static void reset(unsigned count) {
 memset(&cur_cmd,0,sizeof(cur_cmd));memset(&cur_sense_data,0,sizeof(cur_sense_data));memset(&csw,0,sizeof(csw));
 state=RECEIVING_BLOCKS;cur_cmd.block_size=512;cur_cmd.count=count;cur_cmd.sector=100;cur_cmd.data_residue=count*512;cur_cmd.tag=0x1234;
 cur_cmd.data[0]=data0;cur_cmd.data[1]=data1; writes=sends=recvs=0;last_recv=NULL;
}
static void malformed(unsigned count,int length) {
 reset(count); transfer(USB_DIR_OUT,0,length);
 assert(writes==0 && sends==1 && recvs==1 && last_recv==cbw_buffer && last_recv_size==MAX_CBW_SIZE);
 assert(state==WAITING_FOR_CSW_COMPLETION_OR_COMMAND && csw.status==UMS_STATUS_FAIL && csw.signature==CSW_SIGNATURE && csw.tag==0x1234);
 assert(cur_sense_data.sense_key==SENSE_MEDIUM_ERROR && cur_sense_data.asc==ASC_WRITE_ERROR && cur_sense_data.ascq==0);
 assert(cur_cmd.count==count && cur_cmd.sector==100 && cur_cmd.data_select==0);
 unsigned residue=count*512; if(length>0) residue-=MIN(residue,(unsigned)length);assert(csw.data_residue==residue);
 printf("PASS malformed %u-block write, length %d: no storage write; failed CSW, sense, residue and next-CBW receive\n",count,length);
}
int main(void){
 malformed(16,0); malformed(16,4095); malformed(16,4097); malformed(16,8192); malformed(16,-1);
 malformed(2,512);malformed(2,4096);malformed(2,-2147483647);
 reset(16);transfer(USB_DIR_OUT,0,4096);
 assert(writes==1 && written_count==8 && written_sector==100 && written_data==data0 && sends==0 && recvs==1);
 assert(last_recv==data1 && last_recv_size==4096 && state==RECEIVING_BLOCKS && cur_cmd.count==8 && cur_cmd.sector==108 && cur_cmd.data_select==1);
 transfer(USB_DIR_OUT,0,4096);
 assert(writes==2 && written_sector==108 && written_data==data1 && sends==1 && csw.status==UMS_STATUS_GOOD && csw.data_residue==0 && cur_cmd.count==0);
 puts("PASS valid full-buffer then final full-buffer write: double-buffering, addresses, count, GOOD CSW");
 reset(2);transfer(USB_DIR_OUT,0,1024);
 assert(writes==1 && written_count==2 && sends==1 && csw.status==UMS_STATUS_GOOD && csw.data_residue==0);
 puts("PASS valid short final chunk writes exactly two sectors");
 reset(2);transfer(USB_DIR_OUT,-1,1024);
 assert(writes==0 && sends==1 && csw.status==UMS_STATUS_FAIL && csw.data_residue==1024);
 puts("PASS failed hardware transfer never writes data; failure path retained");
 malformed(2,512); commands=0;transfer(USB_DIR_IN,0,sizeof(csw));assert(state==WAITING_FOR_COMMAND && commands==0);transfer(USB_DIR_OUT,0,31);assert(commands==1);
 puts("PASS failure recovery: CSW completion then next CBW dispatches command");
 malformed(2,512);commands=0;transfer(USB_DIR_OUT,0,31);assert(state==WAITING_FOR_CSW_COMPLETION && commands==0);transfer(USB_DIR_IN,0,sizeof(csw));assert(commands==1);
 puts("PASS failure recovery: next CBW arrives before CSW completion and is deferred correctly");
 /* Reinitialize command-specific fields as handle_scsi would. */
 malformed(2,512); reset(2); transfer(USB_DIR_OUT,0,1024);
 assert(writes==1 && sends==1 && csw.status==UMS_STATUS_GOOD);
 puts("PASS subsequent valid command is accepted after protocol reset/reinitialization");
 return 0;
}
'''
with tempfile.TemporaryDirectory() as d:
    d=Path(d);c=d/'test.c';c.write_text(header+function('account_data_transfer')+function('receive_block_data')+function('send_csw')+runner)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(c),'-o',str(d/'test')],check=True)
    result=subprocess.run([str(d/'test')],capture_output=True,text=True,check=True)
    print(result.stdout,end='')
