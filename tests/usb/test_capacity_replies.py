"""Actual 64-bit SCSI reply arms, prefilled with prior disk data.

Checks that large capacity bits survive and an ordinary small disk cannot
inherit high LBA bytes from the previous transfer. No hardware access.
"""
from pathlib import Path
import subprocess
import tempfile
import sys

root = Path(__file__).resolve().parents[2]
source = Path(sys.argv[1]) if len(sys.argv) > 1 else root/'firmware-source/firmware/usbstack/usb_storage.c'
s = source.read_text()
mode = s[s.index('        case SCSI_MODE_SENSE_10:'):s.index('        case SCSI_MODE_SENSE_6:')]
capacity = s[s.index('        case SCSI_READ_CAPACITY_16:'):s.index('        case SCSI_READ_10:')]
structs = '\n'.join(s[s.index('struct '+name+' {'):s.index('} __attribute__ ((packed));', s.index('struct '+name+' {'))+len('} __attribute__ ((packed));')]
                    for name in ['capacity_16','mode_sense_bdesc_longlba','mode_sense_data_10'])
header = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define MIN(a,b) ((a)<(b)?(a):(b))
#define logf(...) ((void)0)
#define LUN_READONLY(lun) false
#define SCSI_MODE_SENSE_10 0x5a
#define SCSI_READ_CAPACITY_16 0x9e
#define SENSE_NOT_READY 2
#define SENSE_ILLEGAL_REQUEST 5
#define ASC_MEDIUM_NOT_PRESENT 0x3a
#define ASC_INVALID_FIELD_IN_CBD 0x24
#define htobe16(x) __builtin_bswap16((uint16_t)(x))
static void store_be64(void *ptr,uint64_t v){unsigned char *p=ptr;for(int i=7;i>=0;i--){p[i]=v;v>>=8;}}
static uint64_t read_be64(const void *ptr){const unsigned char *p=ptr;uint64_t v=0;for(int i=0;i<8;i++)v=(v<<8)|p[i];return v;}
static unsigned find_first_set_bit(unsigned n){return __builtin_ctz(n);}
'''
body = r'''
static unsigned char buffer[128];
static union {struct capacity_16 *capacity_data_16;struct mode_sense_data_10 *ms_data_10;}tb;
static struct {unsigned char command_block[16];}command,*cbw=&command;
static struct {int sense_key,asc,ascq;}cur_sense_data;
static unsigned length=128,bsize=4096,block_size_mult=8;
static uint64_t bcount;
static bool lun_present=true;
static int sends,sent_length;
static void send_command_result(void *p,int n){assert(p==buffer);sends++;sent_length=n;}
static void send_command_failed_result(void){assert(0);}
static void run(int op){switch(op){
'''
runner = r'''
default:assert(0);}}
int main(void){
 tb.capacity_data_16=(void*)buffer;cbw->command_block[2]=0x3f;
 const uint64_t counts[]={1,976773168,0x100000001ULL,0x123456789abULL,0xf123456789abcdefULL};
 for(unsigned i=0;i<sizeof(counts)/sizeof(counts[0]);i++){
  bcount=counts[i];memset(buffer,0xa5,sizeof(buffer));sends=0;
  run(SCSI_READ_CAPACITY_16);
  assert(sends==1 && sent_length==sizeof(struct capacity_16));
  assert(read_be64(tb.capacity_data_16->block_count)==bcount-1);
  assert(buffer[8]==0 && buffer[9]==0 && buffer[10]==0x10 && buffer[11]==0);
  for(unsigned j=sizeof(struct capacity_16);j<sizeof(buffer);j++)assert(buffer[j]==0xa5);
  memset(buffer,0x5a,sizeof(buffer));sends=0;run(SCSI_MODE_SENSE_10);
  assert(sends==1 && sent_length==sizeof(struct mode_sense_data_10));
  assert(read_be64(tb.ms_data_10->block_descriptor.num_blocks)==bcount);
 }
 puts("PASS capacity16/mode10: complete 64-bit counts, poisoned buffer, no writes beyond reply");
}
'''
with tempfile.TemporaryDirectory(prefix='rodbox-capacity-') as t:
    p=Path(t);(p/'test.c').write_text(header+structs+body+mode+capacity+runner)
    subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-function',
                    '-DSTORAGE_64BIT_SECTOR','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
