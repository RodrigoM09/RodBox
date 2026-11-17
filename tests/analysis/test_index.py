"""Real sound_index.c, POSIX temp files and a malloc-backed core allocator.

Checks legacy upgrade, interruption/resume and unchanged-track cache behaviour.
No device or music library is accessed.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2] / 'firmware-source'
HARNESS = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
#include <fcntl.h>
#include "database/sound_index.h"
#undef fsync
#undef close
#undef write
#undef lseek
#undef ftruncate
#undef read
extern int fsync(int);
extern int close(int);
extern ssize_t write(int,const void*,size_t);
extern off_t lseek(int,off_t,int);
extern int ftruncate(int,off_t);
extern ssize_t read(int,void*,size_t);
static int fail_sync, fail_close, fail_write_at, write_calls, fail_seek_at, seek_calls, fail_truncate;
static const char *read_fault_path;
static off_t read_fault_offset;
static int read_fault_nth, read_fault_short;
ssize_t test_read(int fd,void *p,size_t n) {
 struct stat a,b;
 if(read_fault_path && !fstat(fd,&a) && !stat(read_fault_path,&b) &&
    a.st_ino==b.st_ino && lseek(fd,0,SEEK_CUR)==read_fault_offset && --read_fault_nth==0) {
  read_fault_path=NULL;return read_fault_short?read(fd,p,n/2):-1;
 }
 return read(fd,p,n);
}
ssize_t test_write(int fd,const void *p,size_t n) {write_calls++;if(write_calls==fail_write_at)return write(fd,p,n/2);return write(fd,p,n);}
off_t test_lseek(int fd,off_t at,int whence) {seek_calls++;if(seek_calls==fail_seek_at)return -1;return lseek(fd,at,whence);}
int test_ftruncate(int fd,off_t n) {if(fail_truncate){fail_truncate=0;return -1;}return ftruncate(fd,n);}
int test_fsync(int fd) {if(fail_sync){fail_sync=0;return -1;}return fsync(fd);}
int test_close(int fd) {int rc=close(fd);if(fail_close){fail_close=0;return -1;}return rc;}
static void *allocation;
int core_alloc(size_t n) {assert(!allocation);allocation=calloc(1,n);return allocation?1:0;}
void *core_get_data(int h) {assert(h==1);return allocation;}
void core_pin(int h) {assert(h==1);}
void core_unpin(int h) {assert(h==1);}
void core_free(int h) {assert(h==1);free(allocation);allocation=NULL;}
uint64_t path_key_fold_hash(const char *s) {(void)s;return 0;}
static size_t snapshot(const char *path,char *buf,size_t n) {
 int fd=open(path,O_RDONLY);assert(fd>=0);ssize_t got=read(fd,buf,n);assert(got>=0);close(fd);return got;
}
int main(void) {
 struct track_sound s={.period_ms=500,.confidence=70,.analysed_ms=40000};
 struct sound_record r,out;
 struct sound_index_reader reader;
 assert(sizeof(r)==64);
 sound_index_fill(&r,123,100,2000,0,0,&s,TRACK_DECODE_OK);
 assert(r.analysis_revision==SOUND_ANALYSIS_REVISION);
 /* Simulate an existing readable upstream record with the reserved byte 0. */
 r.analysis_revision=0;
 assert(sound_index_begin(1,true)==SOUND_OK);
 assert(sound_index_add(&r));assert(sound_index_finish(false)==SOUND_OK);
 assert(sound_index_reader_open(&reader)==SOUND_OK);
 assert(sound_index_find(&reader,123,&out) && out.analysis_revision==0);
 sound_index_reader_close(&reader);
 assert(sound_index_begin(1,false)==SOUND_OK);
 assert(!sound_index_done(123,100,2000));
 /* Cancelling an upgrade leaves the old finished index readable. */
 sound_index_close();
 assert(sound_index_reader_open(&reader)==SOUND_OK);
 assert(sound_index_find(&reader,123,&out) && out.analysis_revision==0);
 sound_index_reader_close(&reader);
 /* Resume the working file and upgrade in place without duplicate records. */
 assert(sound_index_begin(1,false)==SOUND_OK);
 assert(!sound_index_done(123,100,2000));
 r.analysis_revision=SOUND_ANALYSIS_REVISION;
 assert(sound_index_add(&r));assert(sound_index_count()==1);
 assert(sound_index_done(123,100,2000));
 sound_index_close();
 assert(sound_index_begin(1,false)==SOUND_OK);
 assert(sound_index_done(123,100,2000));
 assert(sound_index_done(123,0,2000));
 assert(!sound_index_done(123,101,2000));
 assert(!sound_index_done(123,100,2001));
 assert(!sound_index_done(456,100,2000));
 sound_index_seen(123);assert(sound_index_finish(true)==SOUND_OK);
 assert(sound_index_reader_open(&reader)==SOUND_OK && reader.count==1);
 assert(sound_index_find(&reader,123,&out) && !memcmp(&r,&out,sizeof(r)));
 sound_index_reader_close(&reader);
 assert(sound_index_begin(1,false)==SOUND_OK);
 assert(sound_index_done(123,100,2000));sound_index_close();
 /* A delayed flush/close error must not publish the replacement index. */
 for(int failure=0;failure<2;failure++) {
  assert(sound_index_begin(3,false)==SOUND_OK);
  r.key=456+failure;assert(sound_index_add(&r));
  if(failure==0)fail_sync=1;else fail_close=1;
  assert(sound_index_finish(false)==SOUND_ERR_IO);
  assert(access("sound.part",F_OK)==0);
  assert(access("sound.dat.new",F_OK)!=0);
  assert(sound_index_reader_open(&reader)==SOUND_OK && reader.count==1);
  assert(sound_index_find(&reader,123,&out));
  assert(!sound_index_find(&reader,r.key,&out));
  sound_index_reader_close(&reader);sound_index_close();
 }
 /* Working append/header errors must not publish, even if finish is called. */
 for(int failure=0;failure<4;failure++) {
  assert(sound_index_begin(20,false)==SOUND_OK);
  write_calls=seek_calls=0;
  if(failure<2)fail_write_at=failure+1;else fail_seek_at=failure-1;
  r.key=700+failure;assert(!sound_index_add(&r));
  fail_write_at=fail_seek_at=0;
  assert(sound_index_finish(false)==SOUND_ERR_IO);sound_index_close();
  assert(access("sound.part",F_OK)!=0);
  assert(sound_index_reader_open(&reader)==SOUND_OK && reader.count==1);
  assert(sound_index_find(&reader,123,&out));sound_index_reader_close(&reader);
 }
 /* A periodic flush failure is not a successful measurement. */
 assert(sound_index_begin(20,false)==SOUND_OK);
 for(int i=0;i<14;i++){r.key=800+i;assert(sound_index_add(&r));}
 fail_sync=1;r.key=900;assert(!sound_index_add(&r));
 assert(sound_index_finish(false)==SOUND_ERR_IO);sound_index_close();
 assert(sound_index_reader_open(&reader)==SOUND_OK && reader.count==1);sound_index_reader_close(&reader);
 /* Failed in-place update is never promoted as a completed index. */
 assert(sound_index_begin(20,false)==SOUND_OK);write_calls=0;fail_write_at=1;r.key=123;
 assert(!sound_index_add(&r));fail_write_at=0;
 assert(sound_index_finish(false)==SOUND_ERR_IO);sound_index_close();
 /* Failed seed write and truncation are failures, rather than an empty index. */
 remove("sound.part");write_calls=0;fail_write_at=2;
 assert(sound_index_begin(20,false)==SOUND_ERR_IO);fail_write_at=0;
 fail_truncate=1;assert(sound_index_begin(20,false)==SOUND_ERR_IO);
 assert(sound_index_begin(20,false)==SOUND_OK);
 assert(sound_index_begin(1,false)==SOUND_ERR_IO);sound_index_close();
 assert(sound_index_begin(2147483647,false)==SOUND_ERR_MEM);
 assert(sound_index_reader_open(&reader)==SOUND_OK && reader.count==1);
 assert(sound_index_find(&reader,123,&out));sound_index_reader_close(&reader);
 /* A transient part read must preserve every byte of resumable work. */
 assert(sound_index_begin(4,false)==SOUND_OK);r.key=456;assert(sound_index_add(&r));r.key=789;assert(sound_index_add(&r));assert(sound_index_close());
 char saved[512],after[512];size_t saved_n=snapshot("sound.part",saved,sizeof(saved));
 for(int where=0;where<2;where++)for(int shortread=0;shortread<2;shortread++){
  read_fault_path="sound.part";read_fault_offset=where?16:0;read_fault_nth=where?1:2;read_fault_short=shortread;
  assert(sound_index_begin(4,false)==SOUND_ERR_IO);
  assert(snapshot("sound.part",after,sizeof(after))==saved_n && !memcmp(saved,after,saved_n));
  assert(sound_index_begin(4,false)==SOUND_OK && sound_index_count()==3);assert(sound_index_close());
 }
 /* If the cheap count read fails, a too-small allocation cannot truncate it. */
 read_fault_path="sound.part";read_fault_offset=0;read_fault_nth=1;read_fault_short=0;
 assert(sound_index_begin(1,false)==SOUND_ERR_IO);
 assert(snapshot("sound.part",after,sizeof(after))==saved_n && !memcmp(saved,after,saved_n));
 /* Failed seeding retains the completed file and removes only the new part. */
 for(int where=0;where<2;where++){
  remove("sound.part");read_fault_path="sound.dat";read_fault_offset=where?16:0;read_fault_nth=where?1:2;
  assert(sound_index_begin(4,false)==SOUND_ERR_IO && access("sound.part",F_OK)!=0);
  assert(sound_index_reader_open(&reader)==SOUND_OK && reader.count==1);sound_index_reader_close(&reader);
 }
 /* Pause flush/close errors are reported and cannot become resumed records. */
 for(int kind=0;kind<2;kind++){
  assert(sound_index_begin(4,false)==SOUND_OK);r.key=456;assert(sound_index_add(&r));
  if(kind)fail_close=1;else fail_sync=1;
  assert(!sound_index_close() && access("sound.part",F_OK)!=0);
  assert(sound_index_reader_open(&reader)==SOUND_OK && reader.count==1);sound_index_reader_close(&reader);
 }
 assert(sound_index_begin(4,false)==SOUND_OK);r.key=123;
 for(int i=0;i<15;i++)assert(sound_index_add(&r));
 fail_sync=1;assert(!sound_index_add(&r));assert(!sound_index_close());
 /* A true interrupted record still recovers the complete records before EOF. */
 assert(sound_index_begin(4,false)==SOUND_OK);r.key=456;assert(sound_index_add(&r));assert(sound_index_close());
 int fd=open("sound.part",O_RDWR);assert(fd>=0);assert(ftruncate(fd,16+64+30)==0);close(fd);
 int done=-1;bool update=false;assert(sound_index_partial(&done,&update) && done==0 && update);
 assert(sound_index_begin(4,false)==SOUND_OK && sound_index_count()==1);assert(sound_index_close());
 assert(sound_index_begin(33554432,true)==SOUND_ERR_MEM);
 /* Completed readers reject a truncated body and counts beyond signed int. */
 fd=open("sound.dat",O_RDWR);assert(fd>=0);assert(ftruncate(fd,16+63)==0);close(fd);
 assert(sound_index_reader_open(&reader)==SOUND_ERR_IO && reader.fd==-1 && reader.count==0);
 fd=open("sound.dat",O_RDWR);assert(fd>=0);uint32_t impossible=UINT32_MAX;
 assert(lseek(fd,8,SEEK_SET)==8 && write(fd,&impossible,4)==4);close(fd);
 assert(sound_index_reader_open(&reader)!=SOUND_OK && reader.fd==-1 && reader.count==0);
 puts("PASS: index upgrade/resume/cache; write and read faults; pause durability; real EOF recovery; bounded readers; completed index preserved; ASan/UBSan");
}
'''
with tempfile.TemporaryDirectory(prefix='rodbox-index-') as tmp:
    d = Path(tmp)
    (d/'system').mkdir()
    (d/'config.h').write_text('/* host filesystem test */\n')
    (d/'system/library_files.h').write_text(
        '#define LIB_SOUND_FILE "sound.dat"\n#define LIB_SOUND_PART "sound.part"\n')
    (d/'file.h').write_text(
        '#include <fcntl.h>\n#include <unistd.h>\n#include <stdio.h>\n'
        '#include <stdbool.h>\n'
        '#define FILE_SIZE_MAX 0x7fffffffu\n'
        'static inline bool file_exists(const char *p){return access(p,F_OK)==0;}\n')
    (d/'core_alloc.h').write_text(
        '#include <stddef.h>\nint core_alloc(size_t);void *core_get_data(int);\n'
        'void core_pin(int);void core_unpin(int);void core_free(int);\n')
    (d/'index.c').write_text(HARNESS)
    binary = d/'index'
    subprocess.run(['clang', '-std=c11', '-D_DARWIN_C_SOURCE', '-O1', '-g',
                    '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                    '-fno-omit-frame-pointer', '-Dfsync=test_fsync', '-Dclose=test_close', '-Dwrite=test_write', '-Dread=test_read', '-Dlseek=test_lseek', '-Dftruncate=test_ftruncate', '-I'+str(d),
                    '-I'+str(ROOT/'apps-ipod'), str(d/'index.c'),
                    str(ROOT/'apps-ipod/database/sound_index.c'),
                    '-o', str(binary)], check=True)
    subprocess.run([str(binary)], cwd=d, check=True)
