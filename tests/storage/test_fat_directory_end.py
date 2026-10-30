"""Production FAT directory insertion must not resurrect records past EOF.

Byte-array directory/cache harness (not a hardware or whole-filesystem test).
--source allows the same regression to demonstrate the previous failure.
"""
from pathlib import Path
import argparse
import importlib.util
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('extractor', Path(__file__).with_name('test_fat_failure_paths.py'))
extractor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extractor)

PREFIX = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define DEBUGF(...) ((void)0)
#define IF_MV(...)
#define strlcpy test_strlcpy
#define RC rc
#define FAT_ERROR(x) do { rc=(x); goto fat_error; } while(0)
#define FAT_RC_ENOSPC (-10)
#define MAX_DIRENTRIES 65536
#define FATLONG_NAME_CHARS 13
#define FATLONG_ORD_F_LAST 0x40
#define ATTR_DIRECTORY 0x10
#define ATTR_LONG_NAME 0x0f
#define ATTR_LONG_NAME_MASK 0x3f
#define DIR_ENTRY_SIZE 32
#define DIR_ENTRIES_PER_SECTOR (fat_bpb->sector_size / DIR_ENTRY_SIZE)
#define ALIGN_UP(x,a) (((x)+(a)-1)/(a)*(a))
#define htole16(x) (x)
#define INT162BYTES(a,p,v) ((a)[p]=(uint16_t)(v),(a)[(p)+1]=(uint16_t)(v)>>8)
/* RAW */
/* FLAGS */
struct bpb { int sector_size,bpb_secperclus; };
struct fat_file { long firstcluster,dircluster; struct {unsigned entry,entries;} e; };
struct fat_filestr {struct fat_file *fatfilep; bool eof; unsigned lastsector;};
static union raw_dirent disk[MAX_DIRENTRIES];
static unsigned allocated,depth,fail_entry,dirty_calls,writes;
static struct bpb bpb;
static void dc_lock_cache(void){depth++;}
static void dc_unlock_cache(void){assert(depth);depth--;}
static void dc_dirty_buf(void *p){assert(p>=(void*)disk && p<(void*)(disk+MAX_DIRENTRIES));dirty_calls++;}
static union raw_dirent *cache_direntry(struct bpb *b,struct fat_filestr *s,unsigned n){
 s->eof=false;s->lastsector=n/(b->sector_size/32);
 if(n==fail_entry || n>=MAX_DIRENTRIES)return NULL;
 if(n>=allocated){s->eof=true;return NULL;}
 return &disk[n];
}
static int fat_extend_dir(struct bpb *b,struct fat_filestr *s){
 (void)s;unsigned more=b->sector_size/32*b->bpb_secperclus;
 assert(allocated+more<=MAX_DIRENTRIES);memset(disk+allocated,0,more*32);allocated+=more;return 0;
}
static bool is_dotdir_name(const char *s){return !strcmp(s,".") || !strcmp(s,"..");}
static size_t strlcpy(unsigned char *d,const char *s,size_t n){size_t z=strlen(s);snprintf((char*)d,n,"%s",s);return z;}
static int check_longname(const char *s){return *s?0:-1;}
static void create_dos_name(unsigned char *out,const char *s,int *n){(void)s;memset(out,'N',11);*n=0;}
static void randomize_dos_name(unsigned char *out,const unsigned char *s,int *n){memcpy(out,s,11);out[0]='A'+((*n)++%26);}
static unsigned long utf16len_utf8(const char *s){return strlen(s);}
static const unsigned char *utf8decode(const unsigned char *s,uint16_t *c){*c=*s;return s+1;}
static void fat_time(uint16_t *d,uint16_t *t,int16_t *n){*d=*t=1;*n=0;}
static void panicf(const char *s,...){fprintf(stderr,"unexpected panic: %s\n",s);abort();}
static uint8_t shortname_checksum(const unsigned char *s){uint8_t x=0;for(int i=0;i<11;i++)x=((x&1)?128:0)+(x>>1)+s[i];return x;}
static unsigned long longent_char_first(void){return 1;}
static unsigned long longent_char_next(unsigned i){return i==9?14:i==24?28:i==30?0:i+2;}
/* SET_CLUSTER */
/* WRITE */
/* ADD */
static void occupied(unsigned i,long cluster){
 memset(&disk[i],0,sizeof(disk[i]));memcpy(disk[i].name,"OLD     TXT",11);
 disk[i].attr=0x20;raw_dirent_set_fstclus(&disk[i],cluster);disk[i].filesize=17651;
}
static void reset(unsigned sector,unsigned count){
 memset(disk,0,sizeof(disk));bpb=(struct bpb){sector,1};allocated=count;depth=0;fail_entry=~0u;dirty_calls=writes=0;
}
static int add(const char *name,unsigned *slot){
 struct fat_file parent={.firstcluster=2},file={.firstcluster=500};
 struct fat_filestr stream={.fatfilep=&parent};
 union raw_dirent template={0};template.attr=0x20;template.filesize=4124;
 int rc=add_dir_entry(&bpb,&stream,&file,name,&template,0,DIRENT_TEMPL_CRT|DIRENT_TEMPL_WRT);
 assert(!depth);*slot=file.e.entry;return rc;
}
static unsigned visible_cluster(unsigned cluster){
 unsigned n=0;for(unsigned i=0;i<allocated && disk[i].name[0];i++)
  if(disk[i].name[0]!=0xe5 && disk[i].attr!=ATTR_LONG_NAME && (((unsigned)disk[i].fstclushi<<16)|disk[i].fstcluslo)==cluster)n++;
 return n;
}
int main(void){
 unsigned slot;
 for(unsigned sector=512;sector<=4096;sector*=2){
  unsigned per=sector/32;
  const char *names[]={"unreadable.txt","unreadable.dat","unreadable.txt.new","unreadable.dat.new"};
  for(unsigned n=0;n<4;n++){
   unsigned needed=(strlen(names[n])+12)/13+1;
   /* Replacing the zero marker previously exposed the stale report after it. */
   reset(sector,per*2);occupied(0,100);occupied(1+needed,4242);
   assert(add(names[n],&slot)==0 && slot==needed);
   assert(visible_cluster(100)==1 && visible_cluster(500)==1);
   assert(visible_cluster(4242)==0 && disk[1+needed].name[0]==0);
   /* Even the slots consumed by a new long name may contain stale data. */
   reset(sector,per*2);occupied(0,100);
   for(unsigned i=2;i<per*2;i++)occupied(i,4242);
   assert(add(names[n],&slot)==0 && visible_cluster(4242)==0);
  }
  /* A deleted gap before a live neighbor must not truncate that neighbor. */
  reset(sector,per);for(unsigned i=0;i<per-1;i++)occupied(i,100+i);
  for(unsigned i=1;i<=3;i++)disk[i].name[0]=0xe5;
  union raw_dirent neighbor=disk[4];assert(add("unreadable.txt",&slot)==0 && slot==3);
  assert(!memcmp(&neighbor,&disk[4],32));
  /* Marker moves across a sector/cluster boundary into an allocated cluster. */
  reset(sector,per*2);for(unsigned i=0;i<per-3;i++)occupied(i,100+i);
  occupied(per,4242);assert(add("unreadable.txt",&slot)==0 && slot==per-1);
  assert(disk[per].name[0]==0 && visible_cluster(4242)==0);
  /* Exact end of chain requires no extra allocation just for the marker. */
  reset(sector,per);for(unsigned i=0;i<per-3;i++)occupied(i,100+i);
  assert(add("unreadable.txt",&slot)==0 && allocated==per);
  /* A long name can extend the chain; the new cluster stays terminated. */
  reset(sector,per);for(unsigned i=0;i<per-1;i++)occupied(i,100+i);
  assert(add("unreadable.txt",&slot)==0 && allocated==per*2 && disk[per+2].name[0]==0);
  /* A failed read of the successor must not publish the new filename. */
  reset(sector,per);occupied(0,100);fail_entry=4;
  assert(add("unreadable.txt",&slot)<0 && disk[1].name[0]==0 && visible_cluster(500)==0);
 }
 /* A full directory cannot store a sentinel beyond the maximum entry count. */
 reset(4096,MAX_DIRENTRIES);for(unsigned i=0;i<MAX_DIRENTRIES-3;i++)occupied(i,100);
 assert(add("unreadable.txt",&slot)==0 && slot==MAX_DIRENTRIES-1);
 puts("PASS FAT end marker: stale records, consumed slots, live neighbors, 512/1024/2048/4096 sectors, boundaries and read failure; ASan/UBSan");
}
'''

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,default=ROOT/'firmware-source/firmware/common/fat.c')
    args=parser.parse_args()
    source=args.source.read_text()
    raw=source[source.index('union raw_dirent\n'):source.index('/* at most 20 LFN entries */')]
    flags=source[source.index('enum add_dir_entry_flags\n'):source.index('struct fatlong_parse_state\n')]
    code=PREFIX.replace('/* RAW */',raw).replace('/* FLAGS */',flags)
    for marker,name in [('SET_CLUSTER','raw_dirent_set_fstclus'),('WRITE','write_longname'),('ADD','add_dir_entry')]:
        code=code.replace('/* '+marker+' */',extractor.extract(source,name))
    with tempfile.TemporaryDirectory(prefix='rodbox-fat-end-') as tmp:
        p=Path(tmp);(p/'test.c').write_text(code)
        subprocess.run(['clang','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-pointer-sign',
                        '-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
        subprocess.run([str(p/'test')],check=True)

if __name__=='__main__':main()
