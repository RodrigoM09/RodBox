"""Production allocator plus duplicate insertion; mocked allocation/CRC services."""
from pathlib import Path
import subprocess,tempfile,sys,os
root=Path(__file__).resolve().parents[2]
s=(Path(sys.argv[1]) if len(sys.argv)>1 else root/'firmware-source/apps-ipod/database/tagcache.c').read_text()
def fn(name):
 a=s.index('static '+('void allocate_tempbuf(' if name=='allocate_tempbuf' else 'bool tempbuf_insert('));b=s.index('{',a);n=1;i=b+1
 while n:n+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[a:i]
header=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#define TAGCACHE_MIN_AUDIO_RESERVE (1024u*1024u)
static size_t free_bytes, reclaimable, owned;
static int allocations,shrinks,frees,fail_alloc,fail_shrink;
static size_t tempbuf_size;static int tempbuf_handle;static char *tempbuf;
static const int buflib_ops_locked;
static char memory[8*1024*1024];
static size_t core_allocatable(void){return free_bytes;}
static int core_alloc_ex(size_t n,const void *ops){
 (void)ops;allocations++;if(fail_alloc || n>free_bytes+reclaimable)return -1;
 if(n>free_bytes){reclaimable-=n-free_bytes;free_bytes=n;}
 free_bytes-=n;owned=n;return 1;
}
static void *core_get_data(int h){assert(h==1);return memory;}
static bool __attribute__((unused)) core_shrink(int h,void *p,size_t n){
 assert(h==1 && p==memory && n<=owned);shrinks++;if(fail_shrink)return false;
 free_bytes+=owned-n;owned=n;return true;
}
static int __attribute__((unused)) core_free(int h){assert(h==1);frees++;free_bytes+=owned;owned=0;return 0;}
static void reset(size_t n,size_t audio){free_bytes=n;reclaimable=audio;owned=0;allocations=shrinks=frees=fail_alloc=fail_shrink=0;tempbuf_size=0;tempbuf_handle=0;tempbuf=NULL;}
'''
extra=r'''
#include <string.h>
#include <strings.h>
#include <ctype.h>
#define logf(...) ((void)0)
struct tempbuf_id_list {long id;struct tempbuf_id_list *next;};
struct tempbuf_searchidx {long idx_id;char *str;int seek;struct tempbuf_id_list idlist;};
static long tempbufidx,tempbuf_left,tempbuf_pos,commit_entry_count,lookup_buffer_depth;
static struct tempbuf_searchidx *lookups[512],**lookup=lookups;
static uint32_t crc_32(const void *v,uint32_t n,uint32_t crc){
 const unsigned char *p=v;while(n--){crc^=*p++;for(int j=0;j<8;j++)crc=(crc>>1)^(0xedb88320u&-(crc&1u));}return crc;
}
'''
runner=r'''
int main(void){
 for(int mode=0;mode<2;mode++)for(size_t odd=0;odd<4;odd++){
  reset(mode?4*1024*1024+odd:64*1024,mode?0:4*1024*1024);
  allocate_tempbuf(128*1024+odd);assert(tempbuf && tempbuf_size>=128*1024+odd);
  tempbufidx=0;commit_entry_count=64;lookup_buffer_depth=512;memset(lookups,0,sizeof(lookups));
  tempbuf_pos=64*sizeof(struct tempbuf_searchidx)+sizeof(lookups);tempbuf_left=tempbuf_size-tempbuf_pos-8;
  char a[]="Example Artist",b[]="example artist",c[]="Another Artist";
  for(int i=0;i<200;i++){assert(tempbuf_insert(i%2?a:b,i,-1,true));assert(tempbufidx==1);assert(lookup[i]==lookup[0]);}
  assert(tempbuf_insert(c,200,-1,true));assert(tempbufidx==2 && lookup[200]!=lookup[0]);
 }
 puts("PASS actual allocator+insertion: duplicate and case-variant artists share one record for all four size alignments, both memory paths; distinct artists remain distinct");
}
'''
with tempfile.TemporaryDirectory() as d:
 d=Path(d);(d/'test.c').write_text(header+extra+fn('allocate_tempbuf')+fn('tempbuf_insert')+runner)
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(d/'test.c'),'-o',str(d/'test')],check=True)
 r=subprocess.run([str(d/'test')],capture_output=True,text=True,env=dict(os.environ,UBSAN_OPTIONS='halt_on_error=1'));print(r.stdout+r.stderr);sys.exit(r.returncode)
