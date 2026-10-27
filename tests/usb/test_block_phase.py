"""Actual READ/WRITE command arms: mismatched host phases never reach disk I/O."""
from pathlib import Path
import importlib.util
import subprocess
import tempfile
import sys
root=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('extract',root/'tests/storage/test_usb_idle.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
p=Path(sys.argv[1]) if len(sys.argv)>1 else root/'firmware-source/firmware/usbstack/usb_storage.c'
s=p.read_text();start=s.index('        case SCSI_READ_10:');arms=s[start:s.index('#if CONFIG_RTC',start)]
start=s.index('static void handle_scsi_ready(struct command_block_wrapper* cbw)\n{')
metadata=s[start:s.index('    storage_get_info(lun,&info);',start)]+'    metadata_reads++;\n}\n'
header=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>
#define STORAGE_64BIT_SECTOR
#define MIN(a,b) ((a)<(b)?(a):(b))
#define logf(...) ((void)0)
#define IF_MD(...)
#define LUN_READONLY(lun) readonly
#define USB_DIR_IN 128
#define USB_DIR_OUT 0
#define EP_IN 129
#define EP_OUT 1
#define UMS_STATUS_GOOD 0
#define UMS_STATUS_FAIL 1
#define SENSE_NOT_READY 2
#define SENSE_ILLEGAL_REQUEST 5
#define SENSE_DATA_PROTECT 7
#define ASC_MEDIUM_NOT_PRESENT 0x3a
#define ASC_WRITE_PROTECTED 0x27
#define ASC_LBA_OUT_OF_RANGE 0x21
#define ASC_INVALID_COMMAND 0x20
#define ASC_LOGICAL_UNIT_NOT_SUPPORTED 0x25
#define CBW_SIGNATURE 0x43425355
#define SCSI_READ_10 0x28
#define SCSI_READ_16 0x88
#define SCSI_WRITE_10 0x2a
#define SCSI_WRITE_16 0x8a
#define READ_BUFFER_SIZE 65536
#define WRITE_BUFFER_SIZE 24576
#define letoh32(x) (x)
typedef uint64_t sector_t;
struct command_block_wrapper {uint32_t signature,tag,data_transfer_length;uint8_t flags,lun,command_length,command_block[16];};
static unsigned char buffer[2*READ_BUFFER_SIZE];
static struct{unsigned char *transfer_buffer;}tb={buffer};
static struct{sector_t sector;unsigned count,block_size,data_select,last_result,failed_write_residue,tag,cur_cmd;void *data[2];}cur_cmd;
static struct{int sense_key,asc,ascq;}cur_sense_data;
static struct command_block_wrapper command,*cbw=&command;
static bool lun_present=true,readonly,host_wrote;
static uint32_t block_size=512,bsize=512,block_size_mult=1;
static sector_t block_count=100000;
static unsigned reads,receives,sends,csws,stalls;static int csw_status;
struct storage_info{int unused;};
static int metadata_reads;
static int storage_num_drives(void){return 1;}
static uint16_t load_be16(const void *v){const uint8_t*p=v;return (p[0]<<8)|p[1];}
static uint32_t load_be32(const void *v){const uint8_t*p=v;return ((uint32_t)p[0]<<24)|(p[1]<<16)|(p[2]<<8)|p[3];}
static uint64_t load_be64(const void *v){const uint8_t*p=v;uint64_t n=0;for(int i=0;i<8;i++)n=(n<<8)|p[i];return n;}
static void store_be32(void *v,uint32_t n){uint8_t*p=v;for(int i=3;i>=0;i--){p[i]=n;n>>=8;}}
static int storage_read_sectors(sector_t s,unsigned n,void*p){assert(s<block_count && n && p);reads++;return 0;}
static void send_csw(int status){csws++;csw_status=status;}
static void send_command_failed_result(void){sends++;}
static void send_and_read_next(void){sends++;}
static void receive_block_data(void *data,int n){assert(data && n>0 && n<=WRITE_BUFFER_SIZE);receives++;}
static void usb_drv_stall(int ep,bool stall,bool in){assert(stall && ep==(in?EP_IN:EP_OUT));stalls++;}
static void fail_command(const struct command_block_wrapper *cbw);
'''
funcs=[]
for name in ['set_transfer_range','block_transfer_matches','reject_command','fail_command']:
    try:funcs.append(m.extract(s,name))
    except ValueError:
        if name not in ['block_transfer_matches','fail_command']:raise
run_prefix=r'''
static void run(int op){switch(op){
'''
runner=r'''
default:assert(0);}}
static void setup(int op,uint32_t count){
 memset(&command,0,sizeof(command));memset(&cur_cmd,0,sizeof(cur_cmd));
 reads=receives=sends=csws=stalls=0;lun_present=true;readonly=false;
 bool in=op==SCSI_READ_10 || op==SCSI_READ_16;
 command.command_block[0]=op;command.flags=in?USB_DIR_IN:USB_DIR_OUT;
 command.data_transfer_length=count*512;
 if(op==SCSI_READ_10 || op==SCSI_WRITE_10){command.command_block[7]=count>>8;command.command_block[8]=count;}
 else store_be32(command.command_block+10,count);
}
int main(void){
 int ops[]={SCSI_READ_10,SCSI_READ_16,SCSI_WRITE_10,SCSI_WRITE_16};
 for(unsigned i=0;i<4;i++){
  int op=ops[i];bool in=i<2;
  for(int bad=0;bad<4;bad++){
   setup(op,8);
   if(bad==0)command.flags^=USB_DIR_IN;
   if(bad==1)command.data_transfer_length=0;
   if(bad==2)command.data_transfer_length=4095;
   if(bad==3)command.data_transfer_length=8192;
   run(op);assert(!reads && !receives && !sends && csws==1 && csw_status==UMS_STATUS_FAIL);
   assert(stalls==(bad!=1));
  }
  setup(op,8);run(op);
  assert(!csws && !stalls && reads==(unsigned)in && receives==(unsigned)!in && sends==(unsigned)in);
  setup(op,0);run(op);assert(!reads && !receives && !sends && csws==1 && csw_status==UMS_STATUS_GOOD);
  setup(op,8);block_count=4;run(op);block_count=100000;
  assert(!reads && !receives && !sends && csws==1 && csw_status==UMS_STATUS_FAIL && stalls==1);
  if(!in){
   setup(op,8);lun_present=false;run(op);assert(!receives && csws==1 && stalls==1);
   setup(op,8);readonly=true;run(op);assert(!receives && csws==1 && stalls==1);
  }
  setup(op,8);command.signature=CBW_SIGNATURE;command.command_length=1;metadata_reads=0;
  handle_scsi_ready(cbw);assert(!metadata_reads && csws==1 && csw_status==UMS_STATUS_FAIL);
  setup(op,8);command.signature=CBW_SIGNATURE;command.command_length=(op==SCSI_READ_10 || op==SCSI_WRITE_10)?10:16;
  handle_scsi_ready(cbw);assert(metadata_reads==1 && !csws);
  setup(op,8);command.signature=CBW_SIGNATURE;command.command_length=16;command.lun=1;command.tag=0x1234;
  metadata_reads=0;cur_cmd.data_residue=999;
  handle_scsi_ready(cbw);assert(!metadata_reads && csws==1 && csw_status==UMS_STATUS_FAIL);
  assert(cur_cmd.data_residue==4096 && cur_cmd.tag==0x1234 && stalls==1);
 }
 /* The byte count itself must not wrap at the BOT 32-bit length boundary. */
 setup(SCSI_WRITE_16,0x80000008u);run(SCSI_WRITE_16);
 assert(!receives && csws==1 && csw_status==UMS_STATUS_FAIL);
 puts("PASS READ/WRITE10/16: direction/short/long/overflow phases rejected before I/O; valid and zero phases retained; refused writes halt data");
}
'''
# cur_cmd.data_residue is only needed by the production zero-count branches.
header=header.replace('unsigned count,block_size,','unsigned count,data_residue,block_size,')
with tempfile.TemporaryDirectory(prefix='rodbox-block-phase-') as t:
    p=Path(t);(p/'test.c').write_text(header+'\n'.join(funcs)+metadata+run_prefix+arms+runner)
    subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-function',
                    '-Wno-undefined-internal','-Wno-unused-variable','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
