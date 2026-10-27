"""Production libfile + CRC, with short-write and late-error injection on temp files."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]/'firmware-source'
harness=r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include "database/libfile.h"
#undef write
#undef fsync
#undef close
#undef read
extern ssize_t write(int,const void*,size_t);
extern int fsync(int);
extern int close(int);
extern ssize_t read(int,void*,size_t);
static int writes,fail_at,fail_sync,fail_close;
static int reads,fail_read_at,short_read;
int fail_size;
ssize_t test_read(int fd,void *p,size_t n){if(++reads==fail_read_at)return short_read?read(fd,p,n/2):-1;return read(fd,p,n);}
ssize_t test_write(int fd,const void *p,size_t n){writes++;return write(fd,p,writes==fail_at?n/2:n);}
int test_sync(int fd){if(fail_sync){fail_sync=0;return -1;}return fsync(fd);}
int test_close(int fd){int r=close(fd);if(fail_close){fail_close=0;return -1;}return r;}
static void seed(void){
 struct libfile_writer w;writes=fail_at=fail_sync=fail_close=0;
 assert(libfile_begin(&w,"data",0x1234,1,4,NULL));
 assert(libfile_write(&w,"ABCD",4,1));assert(libfile_finish(&w,true));
}
static void check_old(void){
 struct libfile_header h;int fd=libfile_open("data",0x1234,1,4,&h,NULL);char b[4];
 assert(fd>=0 && h.count==1);assert(read(fd,b,4)==4 && !memcmp(b,"ABCD",4));close(fd);
}
int main(void){
 seed();struct libfile_writer w;
 assert(libfile_begin(&w,"data",0x1234,1,4,NULL));writes=0;fail_at=1;
 assert(!libfile_write(&w,"EFGH",4,1));fail_at=0;
 assert(!libfile_write(&w,"IJKL",4,1));assert(!libfile_finish(&w,true));check_old();
 char longpath[MAX_PATH+40];memset(longpath,'a',sizeof(longpath)-1);longpath[sizeof(longpath)-1]=0;
 assert(!libfile_begin(&w,longpath,0x1234,1,4,NULL) && w.fd==-1);check_old();
 assert(libfile_begin(&w,"data",0x1234,1,4,NULL));w.hdr.count=UINT32_MAX;
 assert(!libfile_write(&w,"EFGH",4,1));assert(!libfile_finish(&w,true));check_old();
 /* Header short write must restore the old header as well as the old end. */
 writes=0;fail_at=2;assert(!libfile_append("data",0x1234,1,4,"EFGH",1));fail_at=0;check_old();
 struct libfile_marks marks={1,2,3};writes=0;fail_at=1;
 assert(!libfile_set_marks("data",0x1234,1,&marks));fail_at=0;check_old();
 for(int kind=0;kind<2;kind++){
  seed();if(kind)fail_close=1;else fail_sync=1;
  assert(!libfile_append("data",0x1234,1,4,"EFGH",1));
  seed();if(kind)fail_close=1;else fail_sync=1;
  assert(!libfile_set_marks("data",0x1234,1,&marks));
 }
 seed();assert(libfile_append("data",0x1234,1,4,"EFGH",1));
 struct libfile_header h;int fd=libfile_open("data",0x1234,1,4,&h,NULL);assert(fd>=0 && h.count==2);close(fd);
 assert(!libfile_append("zero",0x1234,1,0,"",1));assert(access("zero",F_OK)!=0);
 /* A filesize error is unreadable, not evidence to discard a damaged file. */
 fail_size=1;assert(libfile_open("data",0x1234,1,4,&h,NULL)==LIBFILE_UNREAD);
 assert(!libfile_append("data",0x1234,1,4,"IJKL",1));fail_size=0;
 /* This count used to wrap count*stride to four bytes on native off_t. */
 seed();fd=open("data",O_RDWR);assert(fd>=0);
 uint32_t bad_count=UINT32_C(0x40000001);assert(lseek(fd,8,SEEK_SET)==8 && write(fd,&bad_count,4)==4);close(fd);
 assert(libfile_open("data",0x1234,1,4,&h,NULL)==LIBFILE_BAD);
 writes=0;assert(!libfile_append("data",0x1234,1,4,"IJKL",1));assert(writes==0);
 seed();assert(libfile_begin(&w,"data",0x1234,1,4,NULL));writes=0;
 assert(!libfile_write(&w,"",SIZE_MAX,0) && writes==0);assert(!libfile_finish(&w,true));check_old();
 assert(libfile_begin(&w,"data",0x1234,1,4,NULL));w.bytes=FILE_SIZE_MAX-1;writes=0;
 assert(!libfile_write(&w,"ABCD",4,1) && writes==0);assert(!libfile_finish(&w,true));check_old();
 assert(libfile_begin(&w,"data",0x1234,1,8,NULL));writes=0;
 assert(!libfile_write(&w,"ABCD",4,1) && writes==0);assert(!libfile_finish(&w,true));check_old();
 /* Existing bytes plus a short header read are an I/O fault, not corruption. */
 reads=0;fail_read_at=1;short_read=1;
 assert(libfile_open("data",0x1234,1,4,&h,NULL)==LIBFILE_UNREAD);fail_read_at=0;check_old();
 /* A torn append can be recovered, unless reading its old prefix fails. */
 fd=open("data",O_WRONLY|O_APPEND);assert(fd>=0 && write(fd,"tail",4)==4);close(fd);
 reads=0;fail_read_at=4;short_read=0;
 assert(libfile_open("data",0x1234,1,4,&h,NULL)==LIBFILE_UNREAD);fail_read_at=0;check_old();
 puts("PASS: writer latch; path/count/file-size bounds; torn-header rollback; append/marks late errors; CRC readback; ASan/UBSan");
}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'config.h').write_text('/* host */\n')
 (p/'crc32.h').write_text((root/'firmware/include/crc32.h').read_text())
 (p/'file.h').write_text('#pragma once\n#include <fcntl.h>\n#include <unistd.h>\n#include <sys/stat.h>\n#define MAX_PATH 260\n#define FILE_SIZE_MAX 0x7fffffffu\nextern int fail_size;\nstatic inline off_t ffilesize(int fd){struct stat s;return fail_size||fstat(fd,&s)?-1:s.st_size;}\n')
 (p/'test.c').write_text(harness)
 subprocess.run(['clang','-std=c11','-D_DARWIN_C_SOURCE','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-Dwrite=test_write','-Dread=test_read','-Dfsync=test_sync','-Dclose=test_close','-I'+str(p),'-I'+str(root/'apps-ipod'),str(p/'test.c'),str(root/'apps-ipod/database/libfile.c'),str(root/'firmware/common/crc32.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],cwd=p,check=True)
