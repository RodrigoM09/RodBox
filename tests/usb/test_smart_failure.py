"""Actual SMART reply helper: failed reads cannot send prior sector data."""
from pathlib import Path
import importlib.util
import subprocess
import tempfile
import sys
root=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('extract',root/'tests/storage/test_usb_idle.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
source=Path(sys.argv[1]) if len(sys.argv)>1 else root/'firmware-source/firmware/usbstack/usb_storage.c'
fn=m.extract(source.read_text(),'usb_storage_send_smart')
header=r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define SENSE_MEDIUM_ERROR 3
#define ASC_READ_ERROR 17
struct ata_smart_values{unsigned char data[512];};
static unsigned char buffer[512];
static struct{unsigned char *transfer_buffer;}tb={buffer};
static struct{int count,last_result;void *data[2];}cur_cmd;
static struct{int sense_key,asc,ascq;}cur_sense_data;
static int result,reads,sends,failed;
static int ata_read_smart(struct ata_smart_values *data,uint8_t cmd){assert((void*)data==buffer && cmd==0xd0);reads++;if(!result)memset(data,0x51,sizeof(*data));return result;}
static void send_block_data(void *data,int n){assert(data==buffer && n==512);sends++;}
static void __attribute__((unused)) send_command_failed_result(void){failed++;}
'''
runner=r'''
int main(void){
 const int results[]={-1,(int)0x80000007,1,0};
 for(unsigned i=0;i<sizeof(results)/sizeof(results[0]);i++){
  memset(buffer,0xa5,sizeof(buffer));memset(&cur_sense_data,0,sizeof(cur_sense_data));
  result=results[i];reads=sends=failed=0;cur_cmd.count=99;cur_cmd.last_result=77;
  usb_storage_send_smart(0xd0);assert(reads==1);
  if(result){
   assert(!sends && failed==1 && cur_sense_data.sense_key==SENSE_MEDIUM_ERROR && cur_sense_data.asc==ASC_READ_ERROR);
   for(unsigned j=0;j<sizeof(buffer);j++)assert(buffer[j]==0xa5);
  }else{
   assert(sends==1 && !failed && cur_cmd.count==0 && !cur_cmd.last_result);
   for(unsigned j=0;j<sizeof(buffer);j++)assert(buffer[j]==0x51);
  }
 }
 puts("PASS SMART errors send no stale bytes and report read failure; successful 512-byte reply retained");
}
'''
with tempfile.TemporaryDirectory(prefix='rodbox-smart-') as t:
    p=Path(t);(p/'test.c').write_text(header+fn+runner)
    subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
                    str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
