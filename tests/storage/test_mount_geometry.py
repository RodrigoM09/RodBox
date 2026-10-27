"""Actual FAT mount and BPB checks, with synthetic volumes and no device I/O."""
from pathlib import Path
import re,subprocess,tempfile,sys
from test_fat_failure_paths import extract
root=Path(__file__).resolve().parents[2]
s=(Path(sys.argv[1]) if len(sys.argv)>1 else root/'firmware-source/firmware/common/fat.c').read_text()
constants='\n'.join(re.findall(r'^#define (?:BPB_\w+|FSINFO_\w+|DIR_ENTRY_SIZE|FAT_BAD_MARK)\s+[^\n]+',s,re.M))
# Only numeric constants, not FAT dispatch macros.
constants='\n'.join(x for x in constants.splitlines() if not re.match(r'#define BPB_(FN|CALL)',x))
struct=s[s.index('static struct bpb\n{'):s.index('fat_bpbs[',s.index('static struct bpb\n{'))]
struct=struct[:struct.rfind('}')+1].replace('static struct bpb','struct bpb')+';\n'
code=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#define HAVE_FAT16SUPPORT
#define MAX_VIRT_SECTOR_SIZE 4096
#define STORAGE_GET_INFO
#define BPB_FN_DECL(fn,args...) (*fn##__)(struct bpb *bpb, ##args)
#define BPB_FN_SET16(bpb,fn) ((void)(bpb))
#define BPB_FN_SET32(bpb,fn) ((void)(bpb))
#define IF_MD(a,...)
#define IF_MD_DRV(x) 0
#define DEBUGF(...) ((void)0)
#define LOG_SECTOR_SIZE(bpb) ((bpb)->sector_size)
#define FAT_ERROR(x) do{rc=(x);goto fat_error;}while(0)
#define BYTES2INT16(p,o) ((uint32_t)(p)[o]|((uint32_t)(p)[(o)+1]<<8))
#define BYTES2INT32(p,o) (BYTES2INT16(p,o)|(BYTES2INT16(p,(o)+2)<<16))
typedef uint64_t sector_t;
struct fsinfo {uint32_t freecount,nextfree;};
'''+constants+'\n'+struct+r'''
static unsigned char buffer[4096],boot[4096],fs[4096];
static uint64_t capacity=2000000;
static int reads,releases;
struct storage_info {uint64_t num_sectors;};
static void storage_get_info(int d,struct storage_info *i){(void)d;i->num_sectors=capacity;}
static void *dc_get_buffer(void){return buffer;}
static void dc_release_buffer(void *p){assert(p==buffer);releases++;}
static int storage_read_sectors(sector_t sector,int count,void *p){assert(sector<capacity&&count==1);reads++;memcpy(p,reads==1?boot:fs,4096);return 0;}
static unsigned long cluster2sec(struct bpb *b,long c){return b->firstdatasector+(c-2)*b->bpb_secperclus;}
static void put16(unsigned off,uint16_t v){boot[off]=v;boot[off+1]=v>>8;}
static void put32(unsigned char *p,unsigned off,uint32_t v){for(int i=0;i<4;i++){p[off+i]=v;v>>=8;}}
static struct bpb b;
static void setup(unsigned logical,unsigned virtual_size,bool fat16){
 memset(&b,0,sizeof(b));memset(boot,0,sizeof(boot));memset(fs,0,sizeof(fs));
 b.sector_size=logical;b.startsector=2048;capacity=2000000;reads=releases=0;
 put16(BPB_BYTSPERSEC,virtual_size);boot[BPB_SECPERCLUS]=1;put16(BPB_RSVDSECCNT,32);boot[BPB_NUMFATS]=2;
 boot[BPB_MEDIA]=0xf8;put16(BPB_LAST_WORD,0xaa55);
 if(fat16){put16(BPB_FATSZ16,64);put16(BPB_TOTSEC16,10000);put16(BPB_ROOTENTCNT,512);}
 else{put32(boot,BPB_FATSZ32,1024);put32(boot,BPB_TOTSEC32,100000);put32(boot,BPB_ROOTCLUS,2);put16(BPB_FSINFO,1);}
 put32(fs,FSINFO_SIGNATURE,FSINFO_SIGNATURE_VAL);put32(fs,FSINFO_FREECOUNT,100);put32(fs,FSINFO_NEXTFREE,2);
}
static void bad(void){assert(fat_mount_internal(&b)<0);assert(reads==1&&releases==1);}
'''
# bad() calls actual mount below; declare it before helper.
code=code.replace('static void bad(void)','static int fat_mount_internal(struct bpb *b);\nstatic void bad(void)')
code+=extract(s,'bpb_is_sane')+extract(s,'fat_mount_internal')+r'''
int main(void){
 const unsigned sizes[]={512,1024,2048,4096};
 for(unsigned i=0;i<4;i++)for(unsigned j=i;j<4;j++)for(int f=0;f<2;f++){
  setup(sizes[i],sizes[j],f);assert(fat_mount_internal(&b)==0);assert(b.is_fat16==f);assert(releases==1);assert(reads==(f?1:2));
 }
 setup(512,4096,true);put16(BPB_FATSZ16,10000);put16(BPB_TOTSEC16,50000);
 assert(fat_mount_internal(&b)==0&&b.bpb_fatsz16==80000&&b.fatsize==80000&&b.firstdatasector==(32+2*10000+4)*8);
 setup(512,512,false);capacity=102048;assert(fat_mount_internal(&b)==0);
 setup(512,512,false);boot[BPB_NUMFATS]=1;assert(fat_mount_internal(&b)==0);
 setup(512,512,false);boot[BPB_NUMFATS]=0;bad();
 setup(512,512,false);boot[BPB_NUMFATS]=3;bad();
 setup(512,512,false);put16(BPB_RSVDSECCNT,0);bad();
 setup(512,512,false);put32(boot,BPB_FATSZ32,0);bad();
 setup(512,512,false);put32(boot,BPB_FATSZ32,1);bad();
 setup(512,512,false);put32(boot,BPB_FATSZ32,60000);bad();
 setup(512,4096,false);put32(boot,BPB_TOTSEC32,0x20000000);bad();
 setup(512,4096,false);put32(boot,BPB_FATSZ32,0x20000000);bad();
 setup(512,512,false);capacity=100000;bad();
 setup(512,512,false);put32(boot,BPB_ROOTCLUS,1);bad();
 setup(512,512,false);put32(boot,BPB_ROOTCLUS,100000);bad();
 setup(512,512,false);put16(BPB_FSINFO,32);bad();
 setup(512,512,false);put16(BPB_FSINFO,0);bad();
 setup(512,512,false);boot[BPB_SECPERCLUS]=3;bad();
 setup(512,512,false);boot[BPB_SECPERCLUS]=0;bad();
 setup(512,512,false);put16(BPB_BYTSPERSEC,0);bad();
 setup(512,512,false);put16(BPB_BYTSPERSEC,768);bad();
 setup(512,4096,false);boot[BPB_SECPERCLUS]=128;bad();
 setup(512,512,false);b.is_fat16=true;b.fsinfo.freecount=0xfffffffe;
 put32(fs,FSINFO_FREECOUNT,0xfffffffe);put32(fs,FSINFO_NEXTFREE,1);
 assert(fat_mount_internal(&b)==0&&!b.is_fat16&&b.fsinfo.freecount==UINT32_MAX&&b.fsinfo.nextfree==UINT32_MAX);
 puts("PASS FAT mount: 23 valid FAT16/32 logical/virtual geometries, 18 malformed layouts, stale prior mount and invalid FSInfo hints");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(code)
 subprocess.run(['clang','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
