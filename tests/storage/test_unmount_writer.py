"""The production last-chance writer close must not return into USB handover on error."""
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
#include <limits.h>
#include <setjmp.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
struct filestr_base {int marker;};
struct filestr_desc {struct filestr_base stream;};
static int close_result,closed,panicked;
static jmp_buf fatal_exit;
static int close_internal(struct filestr_desc *f){assert(f->stream.marker==123);closed++;return close_result;}
static _Noreturn void panicf(const char *fmt,...){assert(strstr(fmt,"unmount"));panicked++;longjmp(fatal_exit,1);}
/* ACTUAL */
int main(void){
 (void)&panicf;struct filestr_desc file={{123}};
 close_result=0;force_close_writer_internal(&file.stream);assert(closed==1 && !panicked);
 const int errors[]={-1,-1234,INT_MIN};
 for(unsigned i=0;i<sizeof(errors)/sizeof(errors[0]);i++){
  close_result=errors[i];closed=panicked=0;volatile bool handover=false;
  if(!setjmp(fatal_exit)){force_close_writer_internal(&file.stream);handover=true;}
  assert(closed==1 && panicked==1 && !handover);
 }
 puts("PASS: successful forced close returns; three failed closes halt before cache discard/storage handover");
}
'''
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,default=ROOT/'firmware-source/firmware/common/file.c');args=parser.parse_args()
    actual=module.extract(args.source.read_text(),'force_close_writer_internal')
    with tempfile.TemporaryDirectory(prefix='rodbox-unmount-') as tmp:
        d=Path(tmp);(d/'test.c').write_text(HARNESS.replace('/* ACTUAL */',actual))
        subprocess.run(['clang','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(d/'test.c'),'-o',str(d/'test')],check=True)
        subprocess.run([str(d/'test')],check=True)
if __name__=='__main__':main()
