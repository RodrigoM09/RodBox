"""Exercise the production merge allocator with playback-owned memory."""
from pathlib import Path
import subprocess,tempfile,sys
root=Path(__file__).resolve().parents[2]
p=Path(sys.argv[1]) if len(sys.argv)>1 else root/'firmware-source/apps-ipod/database/tagcache.c'
s=p.read_text();a=s.index('static void allocate_tempbuf(');start=s.index('{',a);depth=1;b=start+1
while depth:
 depth+=(s[b]=='{')-(s[b]=='}');b+=1
fn=s[a:b]
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
call='allocate_tempbuf(128*1024)' if 'size_t minimum' in fn else 'allocate_tempbuf()'
runner='int main(void){reset(64*1024,4*1024*1024);'+call+r''';
 assert(tempbuf_size>=128*1024 && tempbuf_handle==1 && tempbuf==memory);
 assert(free_bytes>=TAGCACHE_MIN_AUDIO_RESERVE && shrinks==1);
 reset(4*1024*1024,0);CALL;assert(tempbuf_size==3*1024*1024 && free_bytes==TAGCACHE_MIN_AUDIO_RESERVE && !shrinks);
 reset(64*1024,4*1024*1024);fail_alloc=1;CALL;assert(!tempbuf_size && !owned && !frees);
 reset(64*1024,4*1024*1024);fail_shrink=1;CALL;assert(!tempbuf_size && !owned && frees==1);
 reset(0,0);CALL;assert(!tempbuf_size && !owned);
 puts("PASS production allocator: bootstrap reclaims playback memory, preserves 1 MiB headroom, ordinary allocation unchanged, allocation/shrink failure cleanup, no-memory refusal");return 0;}
'''.replace('CALL',call)
with tempfile.TemporaryDirectory() as d:
 d=Path(d);(d/'test.c').write_text(header+fn+runner)
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(d/'test.c'),'-o',str(d/'test')],check=True)
 r=subprocess.run([str(d/'test')],capture_output=True,text=True);print(r.stdout+r.stderr);sys.exit(r.returncode)
