"""Actual library-file finalizer against POSIX files and delayed-error injection."""
from pathlib import Path
import importlib.util, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('storage_extract',ROOT/'tests/storage/test_usb_idle.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
actual=module.extract((ROOT/'firmware-source/apps-ipod/database/libfile.c').read_text(),'libfile_finish')
HARNESS=r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include "database/libfile.h"
static int failure, closed, synced, renamed;
static off_t checked_seek(int fd,off_t at,int whence){if(failure==1)return -1;return lseek(fd,at,whence);}
static ssize_t checked_write(int fd,const void *p,size_t n){if(failure==2)return write(fd,p,n/2);return write(fd,p,n);}
static int checked_sync(int fd){synced++;if(failure==3)return -1;return fsync(fd);}
static int checked_close(int fd){closed++;int rc=close(fd);return failure==4?-1:rc;}
static int checked_rename(const char *a,const char *b){renamed++;if(failure==5)return -1;return rename(a,b);}
#define lseek checked_seek
#define write checked_write
#define fsync checked_sync
#define close checked_close
#define rename checked_rename
/* ACTUAL */
#undef lseek
#undef write
#undef fsync
#undef close
#undef rename
int main(void){
 for(failure=0;failure<7;failure++){
  int fd=open("library",O_WRONLY|O_CREAT|O_TRUNC,0600);assert(fd>=0);assert(write(fd,"old",3)==3);assert(close(fd)==0);
  struct libfile_writer w={.hdr={.magic=0x12345678}};
  strcpy(w.path,"library.new");w.fd=open(w.path,O_WRONLY|O_CREAT|O_TRUNC,0600);assert(w.fd>=0);
  assert(write(w.fd,"new",3)==3);closed=synced=renamed=0;
  bool ok=libfile_finish(&w,failure!=6);
  assert(ok==(failure==0));assert(w.fd==-1 && closed==1);
  assert(renamed==((failure==0 || failure==5)?1:0));
  assert(synced==((failure==0 || failure==3 || failure==4 || failure==5)?1:0));
  assert(access("library.new",F_OK)!=0);
  fd=open("library",O_RDONLY);assert(fd>=0);
  if(failure){char b[4]={0};assert(read(fd,b,4)==3 && !strcmp(b,"old"));}
  else{struct libfile_header h;assert(read(fd,&h,sizeof(h))==sizeof(h) && h.magic==0x12345678);}
  assert(close(fd)==0);
 }
 struct libfile_writer invalid={.fd=-1};closed=0;assert(!libfile_finish(&invalid,true));assert(!closed);
 puts("PASS: 8 actual libfile finish cases; delayed errors retain prior file; ASan/UBSan");
}
'''
with tempfile.TemporaryDirectory(prefix='rodbox-libfile-') as tmp:
 d=Path(tmp);(d/'config.h').write_text('/* host */\n')
 (d/'file.h').write_text('#include <fcntl.h>\n#include <unistd.h>\n#define MAX_PATH 260\n')
 (d/'finish.c').write_text(HARNESS.replace('/* ACTUAL */',actual))
 subprocess.run(['clang','-std=c11','-D_DARWIN_C_SOURCE','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(d),'-I'+str(ROOT/'firmware-source/apps-ipod'),str(d/'finish.c'),'-o',str(d/'finish')],check=True)
 subprocess.run([str(d/'finish')],cwd=d,check=True)
