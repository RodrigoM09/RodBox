"""Actual artwork stamp saver propagates libfile publication failures."""
from pathlib import Path
import importlib.util
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('extractor', ROOT/'tests/storage/test_usb_idle.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
actual = module.extract((ROOT/'firmware-source/apps-ipod/metadata/art_cache.c').read_text(), 'aa_stamps_save')
HARNESS = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "database/libfile.h"
#undef write
#undef fsync
#undef close
#undef rename
extern ssize_t write(int,const void*,size_t);
extern int fsync(int),close(int),rename(const char*,const char*);
static int failure,writes;
ssize_t test_write(int fd,const void *p,size_t n){writes++;return write(fd,p,failure>=1 && failure<=3 && writes==failure?n/2:n);}
int test_sync(int fd){return failure==4?-1:fsync(fd);}
int test_close(int fd){int r=close(fd);return failure==5?-1:r;}
int test_rename(const char *a,const char *b){return failure==6?-1:rename(a,b);}
#define AA_SEEN_SLOTS 16384
#define AA_STAMP_BATCH 64
#define AA_STAMP_NONE 0
#define AA_STAMP_FILE "stamps.dat"
#define AA_STAMP_MAGIC 0x1234
#define ART_CACHE_FORMAT_VERSION 8
struct aa_stamp {unsigned int key,stamp;};
struct bg_marks {int entries,commitid,deleted;};
static struct {struct bg_marks done_marks;} art_cache_task={{1,2,0}};
static unsigned int aa_marks_key=100;
static struct aa_stamp aa_stamps[AA_SEEN_SLOTS],aa_stamp_io[AA_STAMP_BATCH];
static unsigned char aa_visited[AA_SEEN_SLOTS/8];
/* ACTUAL */
static size_t snapshot(char *buf){int fd=open(AA_STAMP_FILE,O_RDONLY);assert(fd>=0);ssize_t n=read(fd,buf,4096);assert(n>0);close(fd);return n;}
int main(void){
 char old[4096],after[4096];
 aa_stamps[1]=(struct aa_stamp){1,11};aa_visited[0]=2;assert(aa_stamps_save(true));size_t n=snapshot(old);
 aa_stamps[2]=(struct aa_stamp){2,22};aa_visited[0]|=4;
 for(failure=1;failure<=6;failure++){
  writes=0;assert(!aa_stamps_save(true));
  assert(snapshot(after)==n && !memcmp(old,after,n));assert(access("stamps.dat.new",F_OK)!=0);
 }
 failure=0;assert(aa_stamps_save(true));
 struct libfile_header h;int fd=libfile_open(AA_STAMP_FILE,AA_STAMP_MAGIC,ART_CACHE_FORMAT_VERSION,sizeof(struct aa_stamp),&h,NULL);
 assert(fd>=0 && h.count==3 && h.marks.entries==1 && h.marks.commitid==2);close(fd);
 aa_visited[0]=2;assert(aa_stamps_save(false));
 fd=libfile_open(AA_STAMP_FILE,AA_STAMP_MAGIC,ART_CACHE_FORMAT_VERSION,sizeof(struct aa_stamp),&h,NULL);assert(fd>=0 && h.count==3);close(fd);
 assert(aa_stamps_save(true));fd=libfile_open(AA_STAMP_FILE,AA_STAMP_MAGIC,ART_CACHE_FORMAT_VERSION,sizeof(struct aa_stamp),&h,NULL);assert(fd>=0 && h.count==2);close(fd);
 puts("PASS: artwork stamp writer reports header/body/flush/close/rename failures; prior file and interrupted stamps preserved; ASan/UBSan");
}
'''
with tempfile.TemporaryDirectory(prefix='rodbox-art-stamps-') as tmp:
    d=Path(tmp)
    (d/'config.h').write_text('/* host */\n')
    (d/'file.h').write_text('#pragma once\n#include <fcntl.h>\n#include <unistd.h>\n#include <sys/stat.h>\n#define MAX_PATH 260\nstatic inline off_t ffilesize(int fd){struct stat s;return fstat(fd,&s)?-1:s.st_size;}\n')
    (d/'crc32.h').write_text((ROOT/'firmware-source/firmware/include/crc32.h').read_text())
    (d/'test.c').write_text(HARNESS.replace('/* ACTUAL */',actual))
    subprocess.run(['clang','-std=c11','-D_DARWIN_C_SOURCE','-O1','-g','-Wall','-Wextra','-Werror',
                    '-fsanitize=address,undefined','-Dwrite=test_write','-Dfsync=test_sync','-Dclose=test_close','-Drename=test_rename',
                    '-I'+str(d),'-I'+str(ROOT/'firmware-source/apps-ipod'),str(d/'test.c'),
                    str(ROOT/'firmware-source/apps-ipod/database/libfile.c'),str(ROOT/'firmware-source/firmware/common/crc32.c'),
                    '-o',str(d/'test')],check=True)
    subprocess.run([str(d/'test')],cwd=d,check=True)
