"""Production unreadable-file cache/list retains good lists on failed publication."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2] / 'firmware-source'
HARNESS = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <stdint.h>
#include "database/unreadable.h"
#undef write
#undef fsync
#undef close
#undef rename
extern ssize_t write(int,const void*,size_t);
extern int fsync(int),close(int),rename(const char*,const char*);
static const char *fault_path;
static int fault_op;
static bool target(int fd,int op){
 struct stat a,b;
 if(fault_path && op==fault_op && !fstat(fd,&a) && !stat(fault_path,&b) && a.st_ino==b.st_ino){fault_path=NULL;return true;}
 return false;
}
ssize_t test_write(int fd,const void *p,size_t n){return write(fd,p,target(fd,1)?n/2:n);}
int test_sync(int fd){return target(fd,2)?-1:fsync(fd);}
int test_close(int fd){bool fail=target(fd,3);int rc=close(fd);return fail?-1:rc;}
int test_rename(const char *a,const char *b){if(fault_path && fault_op==4 && !strcmp(a,fault_path)){fault_path=NULL;return -1;}return rename(a,b);}
uint64_t path_key(const char *p){uint64_t n=0;while(*p)n=n*31+(unsigned char)*p++;return n;}
const char *path_key_strip(const char *p){return p;}
int read_line(int fd,char *buf,int max){
 int n=0;char c;ssize_t got=0;
 while(n+1<max && (got=read(fd,&c,1))==1){if(c=='\n')break;buf[n++]=c;}
 buf[n]=0;return got<0?-1:n;
}
static size_t snapshot(const char *path,char *buf){
 int fd=open(path,O_RDONLY);assert(fd>=0);ssize_t n=read(fd,buf,4096);assert(n>0);close(fd);return n;
}
static void seed(void){fault_path=NULL;unreadable_begin();unreadable_add("/old.flac",1);unreadable_end(true);}
int main(void){
 char oldtxt[4096],olddat[4096],after[4096];
 for(int failure=0;failure<6;failure++){
  seed();size_t txt_n=snapshot("unreadable.txt",oldtxt),dat_n=snapshot("unreadable.dat",olddat);
  unreadable_begin();
  fault_path=failure==0 || failure==3 || failure==4?"unreadable.txt.new":"unreadable.dat.new";
  fault_op=failure==0?1:(failure==1 || failure==3?2:(failure==5?4:3));
  unreadable_add("/new.flac",2);unreadable_end(true);assert(!fault_path);
  assert(snapshot("unreadable.txt",after)==txt_n && !memcmp(oldtxt,after,txt_n));
  if(failure==1 || failure==2 || failure==5)
   assert(snapshot("unreadable.dat",after)==dat_n && !memcmp(olddat,after,dat_n));
  assert(access("unreadable.dat.new",F_OK)!=0 && access("unreadable.txt.new",F_OK)!=0);
 }
 seed();unreadable_begin();assert(unreadable_known("/old.flac",1));unreadable_end(true);
 assert(snapshot("unreadable.txt",after)>0);
 unreadable_begin();unreadable_end(true);
 assert(access("unreadable.dat",F_OK)!=0 && access("unreadable.txt",F_OK)!=0);
 puts("PASS: unreadable list short-write/flush/close failures and binary finalization failures retain old list; empty cleanup; ASan/UBSan");
}
'''
with tempfile.TemporaryDirectory(prefix='rodbox-unreadable-') as tmp:
    d = Path(tmp)
    (d/'system').mkdir()
    (d/'config.h').write_text('/* host */\n')
    (d/'system/library_files.h').write_text(
        '#define LIB_UNREADABLE_FILE "unreadable.dat"\n'
        '#define LIB_UNREADABLE_LIST "unreadable.txt"\n'
        '#define LIB_UNREADABLE_MAGIC 0x1234\n#define LIB_UNREADABLE_VERSION 1\n')
    (d/'system/strutil.h').write_text('int read_line(int,char*,int);\n')
    (d/'crc32.h').write_text((ROOT/'firmware/include/crc32.h').read_text())
    (d/'file.h').write_text(
        '#pragma once\n#include <fcntl.h>\n#include <unistd.h>\n#include <sys/stat.h>\n'
        '#define MAX_PATH 260\nstatic inline off_t ffilesize(int fd)'
        '{struct stat s;return fstat(fd,&s)?-1:s.st_size;}\n')
    (d/'test.c').write_text(HARNESS)
    subprocess.run(['clang', '-std=c11', '-D_DARWIN_C_SOURCE', '-DDBTOOL', '-O1', '-g',
                    '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                    '-Dwrite=test_write', '-Dfsync=test_sync', '-Dclose=test_close',
                    '-Drename=test_rename', '-I'+str(d), '-I'+str(ROOT/'apps-ipod'),
                    str(d/'test.c'), str(ROOT/'apps-ipod/database/unreadable.c'),
                    str(ROOT/'apps-ipod/database/libfile.c'), str(ROOT/'firmware/common/crc32.c'),
                    '-o', str(d/'test')], check=True)
    subprocess.run([str(d/'test')], cwd=d, check=True)
