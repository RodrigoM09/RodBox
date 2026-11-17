"""Actual FAT functions on a one-sector metadata cache and a mock FAT disk.

No device access. Supports --source for reproducing failures against the baseline.
"""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]

def extract(source, name):
    match = re.search(r'^(?:static )?(?:void|bool|int|long|unsigned long) ' + name +
                      r'\([^;]*?\)\s*\{', source, re.M)
    if not match:
        raise ValueError(name)
    depth=1
    for token in re.finditer(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|'
                             r"'(?:\\.|[^'\\])*'|[{}]", source[match.end():], re.S):
        depth += (token.group()=='{')-(token.group()=='}')
        if not depth:
            return source[match.start():match.end()+token.end()]
    raise ValueError(name)

PREFIX = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define DEBUGF(...) ((void)0)
#define LIKELY(x) (x)
#define UNLIKELY(x) (x)
#define IF_MV(...)
#define IF_MV_VOL(x) 0
#define HAVE_FAT16SUPPORT
#define FAT_ERROR(value) do {rc=(value);goto fat_error;}while(0)
#define FAT_RC_ENOSPC (-1000)
#define FAT_SEEK_EOF (-1001)
#define FAT_FILE_RW_VAL ((unsigned long)-1)
#define FAT_EOF_MARK 0x0ffffff8
#define FAT16_EOF_MARK 0xfff8
#define FAT_MAX_TRANSFER_SIZE 256
#define CLUSTERS_PER_FAT_SECTOR 128
#define CLUSTERS_PER_FAT16_SECTOR 256
#define LOG_SECTOR_SIZE(bpb) 512
#define letoh16(x) (x)
#define htole16(x) (x)
#define letoh32(x) (x)
#define htole32(x) (x)
typedef uint64_t sector_t;
struct bpb {
 bool is_fat16,mounted;
 unsigned long dataclusters,fatrgnstart,fatsize,bpb_secperclus,firstdatasector,rootdirsectornum;
 long bpb_rootclus;
 struct {unsigned long nextfree,freecount;} fsinfo;
};
struct fat_file {long firstcluster,dircluster;};
struct fat_filestr {struct fat_file *fatfilep;long lastcluster,clusternum;sector_t lastsector;unsigned long sectornum;bool eof;};
struct fat_direntry {int unused;};
static struct bpb bpb;
#define FAT_BPB(volume) (&bpb)
static uint32_t disk_fat[16][128],cache_data[128];
static long cached_sector;
static bool dirty,dir_dirty;
static unsigned long directory_cluster,durable_directory_cluster;
static int misses,fail_miss,bad_access,depth,transfers,fail_directory;
static char order[64];static int order_n;
static void dc_lock_cache(void){depth++;}
static void dc_unlock_cache(void){assert(depth>0);depth--;}
static void commit_buffer(void){if(dirty){assert(cached_sector>=20 && cached_sector<36);memcpy(disk_fat[cached_sector-20],cache_data,512);dirty=false;order[order_n++]='F';}}
static void *cache_sector(struct bpb *p,sector_t sector){
 (void)p;
 if(sector<20 || sector>=36){bad_access++;return NULL;}
 if(cached_sector==(long)sector)return cache_data;
 commit_buffer();cached_sector=-1;
 if(++misses==fail_miss)return NULL;
 memcpy(cache_data,disk_fat[sector-20],512);cached_sector=sector;return cache_data;
}
static void dc_dirty_buf(void *p){assert(p==(void*)cache_data);dirty=true;}
static void cache_commit(struct bpb *p){(void)p;commit_buffer();if(dir_dirty){durable_directory_cluster=directory_cluster;dir_dirty=false;order[order_n++]='D';}}
static _Noreturn void panicf(const char *s,...){fprintf(stderr,"unexpected panic: %s\n",s);abort();}
static int update_short_entry(struct bpb *p,struct fat_file *f,uint32_t size,struct fat_direntry *d){
 (void)p;(void)size;(void)d;if(fail_directory)return -1;directory_cluster=f->firstcluster;dir_dirty=true;return 0;
}
static void fat_empty_fat_direntry(struct fat_direntry *d){(void)d;}
static long transfer(struct bpb *p,sector_t sector,long count,char *buf,bool write){(void)p;(void)sector;(void)buf;(void)write;assert(count>0);transfers++;return 0;}
static long get_next_cluster32(struct bpb*,long);
static long get_next_cluster16(struct bpb*,long);
static int update_fat_entry32(struct bpb*,unsigned long,unsigned long);
static int update_fat_entry16(struct bpb*,unsigned long,unsigned long);
static long find_free_cluster32(struct bpb*,long);
static long find_free_cluster16(struct bpb*,long);
#define get_next_cluster(p,n) ((p)->is_fat16?get_next_cluster16(p,n):get_next_cluster32(p,n))
#define update_fat_entry(p,n,v) ((p)->is_fat16?update_fat_entry16(p,n,v):update_fat_entry32(p,n,v))
#define find_free_cluster(p,n) ((p)->is_fat16?find_free_cluster16(p,n):find_free_cluster32(p,n))
void fat_rewind(struct fat_filestr*);
'''

SUFFIX = r'''
static void set(unsigned cl,uint32_t val){disk_fat[cl/128][cl%128]=val;}
static uint32_t get(unsigned cl){if(cached_sector==(long)(20+cl/128))return cache_data[cl%128]&0xfffffff;return disk_fat[cl/128][cl%128]&0xfffffff;}
static void reset(void){
 memset(disk_fat,0,sizeof(disk_fat));memset(cache_data,0,sizeof(cache_data));
 bpb=(struct bpb){.dataclusters=1022,.fatrgnstart=20,.fatsize=8,.bpb_secperclus=8,.firstdatasector=100,.bpb_rootclus=2,.fsinfo={3,1000},.mounted=true};
 cached_sector=-1;dirty=dir_dirty=false;misses=fail_miss=bad_access=depth=transfers=fail_directory=order_n=0;
 directory_cluster=durable_directory_cluster=10;set(2,FAT_EOF_MARK);set(10,FAT_EOF_MARK);
}
int main(int argc,char **argv){
 const char *scenario=argc>1?argv[1]:"all";bool all=!strcmp(scenario,"all");
 if(all || !strcmp(scenario,"allocate")){
  const int failures[]={4,3,1,2,5,6};
  for(unsigned i=0;i<sizeof(failures)/sizeof(failures[0]);i++){
   reset();for(int cl=2;cl<130;cl++)set(cl,FAT_EOF_MARK);fail_miss=failures[i];
   long cl=next_write_cluster(&bpb,10);
   assert(!bad_access && depth==0);
   /* A live link may never point to a free cluster, even on an error. */
   assert(get(10)>=FAT_EOF_MARK || (get(10)>=2 && get(get(10))!=0));
   if(cl>0)assert(get(10)==(unsigned)cl && get(cl)>=FAT_EOF_MARK);
  }
  puts("PASS allocation failure cannot publish a link to an unallocated cluster");
 }
 if(all || !strcmp(scenario,"free")){
  reset();set(10,130);set(130,FAT_EOF_MARK);fail_miss=1;
  assert(free_cluster_chain(&bpb,10)<0);assert(get(10)==130 && get(130)>=FAT_EOF_MARK && !bad_access && !depth);
  reset();set(10,130);set(130,FAT_EOF_MARK);fail_miss=2;
  assert(free_cluster_chain(&bpb,10)==0);assert(get(10)==0 && get(130)>=FAT_EOF_MARK && !bad_access && !depth);
  reset();set(10,130);set(130,FAT_EOF_MARK);assert(free_cluster_chain(&bpb,10)==1);assert(!get(10) && !get(130));
  puts("PASS chain-read errors stop before freeing that cluster or touching an error-code address");
 }
 if(all || !strcmp(scenario,"truncate")){
  reset();set(10,130);set(130,FAT_EOF_MARK);fail_miss=1;
  struct fat_file f={10,2};struct fat_filestr s={.fatfilep=&f,.lastcluster=10};
  assert(fat_truncate(&s)<0);assert(get(10)==130 && get(130)>=FAT_EOF_MARK && !bad_access);
  fail_miss=0;assert(fat_truncate(&s)>0);assert(get(10)>=FAT_EOF_MARK && !get(130));
  puts("PASS failed truncate lookup preserves the live tail");
 }
 if(all || !strcmp(scenario,"empty")){
  reset();fail_directory=1;struct fat_file f={10,2};struct fat_filestr s={.fatfilep=&f,.lastcluster=10};
  assert(fat_closewrite(&s,0,NULL)<0);assert(f.firstcluster==10 && durable_directory_cluster==10 && get(10)>=FAT_EOF_MARK);
  fail_directory=0;assert(fat_closewrite(&s,0,NULL)==0);assert(!f.firstcluster && !durable_directory_cluster && !get(10));
  assert(order_n>=2 && order[0]=='D' && order[order_n-1]=='F');
  reset();set(10,130);set(130,FAT_EOF_MARK);f.firstcluster=10;s.lastcluster=10;
  assert(fat_closewrite(&s,0,NULL)==0 && !get(10) && !get(130));
  puts("PASS empty-file directory reference is committed before its first cluster is freed");
 }
 if(all || !strcmp(scenario,"bounds")){
  reset();assert(get_next_cluster32(&bpb,-1)<0 && !bad_access);
  assert(update_fat_entry32(&bpb,(unsigned long)-1,0)<0 && !bad_access);
  assert(get_next_cluster32(&bpb,1024)<0 && update_fat_entry32(&bpb,1024,0)<0 && !bad_access);
  set(10,1);assert(get_next_cluster32(&bpb,10)<0);
  reset();set(10,0);assert(get_next_cluster32(&bpb,10)<0);
  reset();bpb.is_fat16=true;assert(get_next_cluster16(&bpb,-2)==-1);assert(get_next_cluster16(&bpb,-1)==0);
  assert(update_fat_entry16(&bpb,(unsigned long)-1,0)<0 && !bad_access);
  puts("PASS invalid/free/reserved cluster links rejected; FAT16 root pseudo-clusters retained");
 }
 if(all || !strcmp(scenario,"stream")){
  reset();set(10,130);set(130,FAT_EOF_MARK);fail_miss=1;
  struct fat_file f={10,2};struct fat_filestr s={.fatfilep=&f,.lastcluster=10,.lastsector=171,.sectornum=7};char buf[512];
  assert(fat_readwrite(&s,1,buf,false)<0 && transfers==0 && !bad_access);
  reset();set(10,130);set(130,FAT_EOF_MARK);fail_miss=1;fat_rewind(&s);
  assert(fat_seek(&s,9)<0 && !bad_access && s.lastsector==0);
  puts("PASS failed chain lookup cannot become a successful sector transfer or seek");
 }
}
'''

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,default=ROOT/'firmware-source/firmware/common/fat.c')
    parser.add_argument('--scenario',default='all',choices=['all','allocate','free','truncate','empty','bounds','stream'])
    args=parser.parse_args()
    source=args.source.read_text()
    actual='\n\n'.join(extract(source,name) for name in (
        'cluster2sec','get_next_cluster16','find_free_cluster16','update_fat_entry16',
        'get_next_cluster32','find_free_cluster32','update_fat_entry32',
        'next_write_cluster','free_cluster_chain','fat_truncate','fat_closewrite',
        'fat_readwrite','fat_rewind','fat_seek'))
    with tempfile.TemporaryDirectory(prefix='rodbox-fat-') as tmp:
        d=Path(tmp);(d/'test.c').write_text(PREFIX+actual+SUFFIX)
        subprocess.run(['clang','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror',
                        '-fsanitize=address,undefined',str(d/'test.c'),'-o',str(d/'test')],check=True)
        subprocess.run([str(d/'test'),args.scenario],check=True)

if __name__=='__main__':main()
