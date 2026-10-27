"""Exercise actual disk_init with failed/partial reads and malformed GPT sizes."""
from pathlib import Path
import subprocess,tempfile,sys
root=Path(__file__).resolve().parents[2]
s=Path(sys.argv[1]).read_text() if len(sys.argv)>1 else (root/'firmware-source/firmware/common/disk.c').read_text()
macros=s[s.index('#define BYTES2INT64'):s.index('static struct partinfo part')]
fn=s[s.index('bool disk_init('):s.index('\nbool disk_partinfo(')]
header=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#define IF_MD_NONVOID(x) void
#define IF_MD(a,...)
#define IF_MD_DRV(x) 0
#define CHECK_DRV(x) 1
#define SECTOR_SIZE 512
#define STORAGE_ATA 1
#define CONFIG_STORAGE STORAGE_ATA
#define MAX_VARIABLE_LOG_SECTOR 4096
#define DC_CACHE_BUFSIZE 4096
static unsigned short disk_log_sector_size[1]={512};
#define LOG_SECTOR_SIZE(x) disk_log_sector_size[0]
#define panicf(...) assert(0)
#define MAX_PARTITIONS_PER_DRIVE 4
#define PARTITION_TYPE_GPT_GUARD 0xee
#define PARTITION_TYPE_FAT32_LBA 0x0c
#define DEBUGF(...) ((void)0)
#define disk_writer_lock() ((void)0)
#define disk_writer_unlock() ((void)0)
typedef uint64_t sector_t;
struct storage_info {sector_t num_sectors;unsigned sector_size;};
struct partinfo {unsigned type;sector_t start,size;};
static struct partinfo part[4];
#ifdef MAX_VIRT_SECTOR_SIZE
static unsigned disk_sector_multiplier[1];
#endif
static unsigned char buffer[4096], mbr[4096],gpt[4096],entries[4096];
static int scenario, calls,releases;
static unsigned reported_size=512;
static uint64_t reported_count=10000;
static void *dc_get_buffer(void){return buffer;}
static void dc_release_buffer(void *p){assert(p==buffer);releases++;}
static void storage_get_info(int d,struct storage_info *i){(void)d;i->num_sectors=reported_count;i->sector_size=reported_size;}
static int storage_read_sectors(sector_t l,int n,void *p){
 assert(n==1);assert(++calls<100);
 if(l==0){memcpy(p,mbr,reported_size);return scenario==1?-1:0;}
 if(l==1){memcpy(p,gpt,reported_size);return scenario==2?-1:0;}
 if(l==2){memcpy(p,entries,reported_size);return scenario==3?-1:0;}
 memset(p,0,reported_size);return -1;
}
static void put32(unsigned char *p,uint32_t v){for(int i=0;i<4;i++){p[i]=v;v>>=8;}}
static void setup(void){
 memset(part,0,sizeof(part));memset(mbr,0,sizeof(mbr));memset(gpt,0,sizeof(gpt));memset(entries,0,sizeof(entries));
 mbr[510]=0x55;mbr[511]=0xaa;mbr[0x1be + 4]=0xee;
 memcpy(gpt,"EFI PART",8);put32(gpt+8,0x10000);put32(gpt+12,0x5c);put32(gpt+24,1);
 put32(gpt+72,2);put32(gpt+80,4);put32(gpt+84,128);
 const unsigned char guid[]={0xa2,0xa0,0xd0,0xeb,0xe5,0xb9,0x33,0x44,0x87,0xc0,0x68,0xb6,0xb7,0x26,0x99,0xc7};
 memcpy(entries,guid,16);put32(entries+32,34);put32(entries+40,100);
 calls=releases=0;
}
'''
main=r'''
int main(void){
 setup();scenario=0;assert(disk_init());assert(part[0].type==0x0c&&part[0].start==34);assert(releases==1);
 setup();scenario=1;assert(!disk_init());assert(releases==1);
 setup();scenario=2;disk_init();assert(part[0].type!=0x0c);
 setup();scenario=3;disk_init();assert(part[0].type!=0x0c);
 const unsigned sizes[]={0,1,64,127,129,300,511,513,0xffffffff};
 for(unsigned i=0;i<sizeof(sizes)/sizeof(sizes[0]);i++){setup();scenario=0;put32(gpt+84,sizes[i]);disk_init();assert(part[0].type!=0x0c);assert(releases==1);}
 reported_count=0;setup();assert(!disk_init()&&calls==0);reported_count=10000;
 const unsigned bad_sizes[]={0,1,256,513,768};
 for(unsigned i=0;i<sizeof(bad_sizes)/sizeof(bad_sizes[0]);i++){reported_size=bad_sizes[i];setup();assert(!disk_init()&&calls==0&&releases==1);}
 const unsigned sectors[]={512,1024,2048,4096};
 for(unsigned i=0;i<sizeof(sectors)/sizeof(sectors[0]);i++){
  reported_size=sectors[i];setup();scenario=0;
  assert(disk_init() && part[0].type==0x0c && part[0].start==34);
  assert(disk_log_sector_size[0]==reported_size && releases==1);
  for(unsigned entry_size=128;entry_size<=reported_size;entry_size*=2){
   setup();put32(gpt+80,1);put32(gpt+84,entry_size);
   assert(disk_init() && part[0].type==0x0c && part[0].start==34);
  }
 }
 /* A native 4K sector must be scanned beyond the first 512 bytes. */
 reported_size=4096;setup();scenario=0;
 memcpy(entries+1024,entries,128);memset(entries,0,1024);put32(gpt+80,9);
 assert(disk_init() && part[0].type==0x0c && part[0].start==34);
 puts("PASS disk_init: valid GPT, partial failed MBR/header/table reads and nine malformed entry sizes");
 puts("PASS ATA/native-sector assignment: 512/1024/2048/4096, all supported GPT entry sizes, native-4K entry past byte 512");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(header+macros+fn+main)
 for flags in [[],['-DDEFAULT_VIRT_SECTOR_SIZE=4096','-DMAX_VIRT_SECTOR_SIZE=4096']]:
  subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',*flags,str(p/'test.c'),'-o',str(p/'test')],check=True)
  subprocess.run([str(p/'test')],check=True)
