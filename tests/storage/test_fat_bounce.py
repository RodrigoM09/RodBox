"""Production FAT bounce transfer does not copy failed read buffers to callers."""
from pathlib import Path
import argparse
import importlib.util
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('fat_extract',Path(__file__).with_name('test_fat_failure_paths.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
HARNESS=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define DEBUGF(...) ((void)0)
#define IF_MD(...)
#define UNLIKELY(x) (x)
#define MIN(a,b) ((a)<(b)?(a):(b))
#define STORAGE_NEEDS_BOUNCE_BUFFER
#define STORAGE_OVERLAP(p) (true)
#define LOG_SECTOR_SIZE(p) 512
#define FAT_BOUNCE_SECTORS 2
#define BOUNCE_SECTOR_SIZE 512
#define FAT_BOUNCE_BUFFER(p) bounce
typedef uint64_t sector_t;
struct bpb {sector_t startsector,firstdatasector,totalsectors;};
static unsigned char bounce[1024],destination[2560],expected[2560];
static int reads,fail_at,partial;
static int storage_read_sectors(sector_t start,long count,void *buf){
 reads++;assert(start>=100 && count>0 && count<=2);
 size_t bytes=count*512;if(reads==fail_at){memset(buf,0xee,partial==2?bytes:partial==1?bytes/2:0);return -1;}
 for(size_t n=0;n<bytes;n++)((unsigned char*)buf)[n]=(unsigned char)((start-100)*512+n);
 return 0;
}
static int storage_write_sectors(sector_t start,long count,const void *buf){(void)start;(void)count;(void)buf;return 0;}
static _Noreturn void panicf(const char *s,...){(void)s;abort();}
/* ACTUAL */
int main(void){
 struct bpb b={.firstdatasector=100,.totalsectors=1000};
 for(int mode=0;mode<3;mode++){
  memset(destination,0x5a,sizeof(destination));memcpy(expected,destination,sizeof(expected));
  partial=mode;fail_at=1;reads=0;assert(transfer(&b,100,5,(char*)destination,false)<0);
  assert(!memcmp(destination,expected,sizeof(destination)));
 }
 memset(destination,0x5a,sizeof(destination));memcpy(expected,destination,sizeof(expected));
 for(int i=0;i<1024;i++)expected[i]=(unsigned char)i;
 fail_at=2;reads=0;assert(transfer(&b,100,5,(char*)destination,false)<0 && reads==2);
 assert(!memcmp(destination,expected,sizeof(destination)));
 fail_at=0;reads=0;assert(transfer(&b,100,5,(char*)destination,false)==0 && reads==3);
 for(unsigned i=0;i<sizeof(destination);i++)assert(destination[i]==(unsigned char)i);
 puts("PASS: failed bounce reads preserve caller bytes; successful preceding chunks and complete multi-chunk reads retained");
}
'''
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,default=ROOT/'firmware-source/firmware/common/fat.c');args=parser.parse_args()
    actual=module.extract(args.source.read_text(),'transfer')
    with tempfile.TemporaryDirectory(prefix='rodbox-fat-bounce-') as tmp:
        d=Path(tmp);(d/'test.c').write_text(HARNESS.replace('/* ACTUAL */',actual))
        subprocess.run(['clang','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(d/'test.c'),'-o',str(d/'test')],check=True)
        subprocess.run([str(d/'test')],check=True)
if __name__=='__main__':main()
