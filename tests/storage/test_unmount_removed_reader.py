"""Production unmount callback and close path: replaced files must be freed.

Runs on a mock FAT chain, never a device. --source-root accepts the old source
so the original leaked-cluster behaviour can be reproduced with the same test.
"""
from pathlib import Path
import argparse
import importlib.util
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    'extract', Path(__file__).with_name('test_fat_failure_paths.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

HARNESS = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <errno.h>
#include <setjmp.h>
#include <string.h>
#define FD_WRITE 1
#define FO_SINGLE 2
#define FO_REMOVED 4
#define FAT_RM_DATA 1
#define DEBUGF(...) ((void)0)
#define FILE_ERROR(e,r) do { errno=(e);rc=(r);goto file_error; } while(0)
struct fat_file { int firstcluster; };
struct file_base_info { struct fat_file fatfile; };
struct filestr_base { unsigned flags;struct file_base_info *infop; };
static struct file_base_info info;
static unsigned readers;
static bool removed,allocated,fail_free,panicked;
static unsigned frees;
static jmp_buf stopped;
static unsigned fileobj_get_flags(struct filestr_base *s)
{ assert(s->infop==&info);return (readers==1?FO_SINGLE:0)|(removed?FO_REMOVED:0); }
static int fat_remove(struct fat_file *f,int what)
{
 assert(f==&info.fatfile && what==FAT_RM_DATA && removed);
 if(fail_free)return -1;
 assert(allocated);allocated=false;frees++;f->firstcluster=0;return 0;
}
static void fileop_onclose_internal(struct filestr_base *s)
{ assert(readers && s->infop==&info);readers--; }
static void panicf(const char *fmt,...)
{ assert(strstr(fmt,"unmount"));panicked=true;longjmp(stopped,1); }
/* CLOSE */
/* FORCE_READER */
static void force_close_writer_internal(struct filestr_base *s)
{ if(close_stream_internal(s)<0)panicf("writer unmount"); }
/* CALLBACK */
static void setup(unsigned count,bool gone)
{ readers=count;removed=gone;allocated=true;fail_free=panicked=false;frees=0;info.fatfile.firstcluster=42; }
int main(void)
{
 (void)&panicf;
 struct filestr_base stream={0,&info};
 for(unsigned n=1;n<=4;n++)for(unsigned writer=0;writer<=n;writer++){
  setup(n,true);
  for(unsigned i=0;i<n;i++){
   stream.flags=(writer==i+1)?FD_WRITE:0;
   fileop_onunmount_internal(&stream);
   assert(readers==n-i-1);
   assert(allocated==(readers!=0));
  }
  assert(frees==1 && !panicked);
 }
 puts("PASS replaced/deleted files: last reader or writer frees chain exactly once");
 for(unsigned n=1;n<=4;n++){
  setup(n,false);stream.flags=0;
  for(unsigned i=0;i<n;i++)fileop_onunmount_internal(&stream);
  assert(!readers && allocated && !frees);
 }
 puts("PASS live music/artwork readers: no clusters freed");
 setup(1,true);fail_free=true;stream.flags=0;
 volatile bool handed_over=false;
 if(!setjmp(stopped)){fileop_onunmount_internal(&stream);handed_over=true;}
 assert(panicked && !handed_over && allocated && !frees);
 puts("PASS failed chain cleanup stops before USB handover");
}
'''

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source-root', type=Path, default=ROOT/'firmware-source')
    args = p.parse_args()
    common = (args.source_root/'firmware/common/file_internal.c').read_text()
    redirect = (args.source_root/'firmware/include/dircache_redirect.h').read_text()
    callback = module.extract(redirect.replace('static inline void', 'static void'),
                              'fileop_onunmount_internal')
    force = (module.extract(common, 'force_close_reader_internal')
             if 'void force_close_reader_internal(' in common else '')
    code = HARNESS.replace('/* CLOSE */', module.extract(common, 'close_stream_internal'))
    code = code.replace('/* FORCE_READER */', force).replace('/* CALLBACK */', callback)
    with tempfile.TemporaryDirectory(prefix='rodbox-removed-reader-') as tmp:
        d = Path(tmp)
        (d/'test.c').write_text(code)
        subprocess.run(['clang','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror',
                        '-fsanitize=address,undefined',str(d/'test.c'),'-o',str(d/'test')],check=True)
        subprocess.run([str(d/'test')], check=True)

if __name__ == '__main__':
    main()
