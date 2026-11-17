"""Production calibration persistence: incomplete reads and delayed write errors."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2] / 'firmware-source'
HARNESS = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include "database/sound_cal.h"
#include "database/sound_mix.h"
#undef write
#undef fsync
#undef close
#undef rename
extern ssize_t write(int,const void*,size_t);
extern int fsync(int),close(int),rename(const char*,const char*);
static int fail_read_at=-1,fail_write_at,writes,fail_sync,fail_close,fail_rename,axis_shift;
ssize_t test_write(int fd,const void *p,size_t n){return write(fd,p,++writes==fail_write_at?n/2:n);}
int test_sync(int fd){if(fail_sync){fail_sync=0;return -1;}return fsync(fd);}
int test_close(int fd){int r=close(fd);if(fail_close){fail_close=0;return -1;}return r;}
int test_rename(const char *a,const char *b){if(fail_rename){fail_rename=0;return -1;}return rename(a,b);}
bool sound_index_exists(void){return true;}
int sound_index_reader_open(struct sound_index_reader *r){r->count=500;r->fd=-1;return SOUND_OK;}
void sound_index_reader_close(struct sound_index_reader *r){(void)r;}
bool sound_index_read(struct sound_index_reader *r,int n,struct sound_record *out){
 (void)r;if(n==fail_read_at)return false;memset(out,0,sizeof(*out));out->key=n+1;out->analysed_s=40;return true;
}
bool sound_record_usable(const struct sound_record *r){return r->analysed_s>0;}
void sound_mix_axes(const struct sound_record *r,struct sound_axes *out){
 memset(out,0,sizeof(*out));out->energy=((r->key+axis_shift)%500)*2;
}
static size_t snapshot(char *buf){
 int fd=open("cal.dat",O_RDONLY);assert(fd>=0);ssize_t n=read(fd,buf,8192);assert(n>0);close(fd);return n;
}
int main(void){
 assert(sound_cal_update());assert(sound_cal_at(CAL_ENERGY,500)>=490);
 char saved[8192],after[8192];size_t n=snapshot(saved);
 /* Fingerprinting succeeds; the calibration pass then fails after 350 tracks. */
 fail_read_at=350;assert(!sound_cal_update());assert(sound_cal_at(CAL_ENERGY,500)==-1);
 assert(snapshot(after)==n && !memcmp(saved,after,n));fail_read_at=-1;
 for(int failure=0;failure<5;failure++){
  writes=0;fail_write_at=failure<2?failure+1:0;
  fail_sync=failure==2;fail_close=failure==3;fail_rename=failure==4;
  assert(!sound_cal_update());fail_write_at=0;
  assert(snapshot(after)==n && !memcmp(saved,after,n));assert(access("cal.dat.new",F_OK)!=0);
 }
 assert(sound_cal_update());assert(sound_cal_at(CAL_ENERGY,500)>=490);
 puts("PASS: complete calibration pass required; short writes, flush/close/rename errors retain prior file; ASan/UBSan");
}
'''
with tempfile.TemporaryDirectory(prefix='rodbox-cal-') as tmp:
    d = Path(tmp)
    (d/'system').mkdir()
    (d/'config.h').write_text('/* host */\n')
    (d/'system.h').write_text('/* host */\n')
    (d/'system/library_files.h').write_text('#define LIB_SOUND_CAL_FILE "cal.dat"\n')
    (d/'file.h').write_text('#include <fcntl.h>\n#include <unistd.h>\n#include <stdio.h>\n')
    (d/'test.c').write_text(HARNESS)
    subprocess.run(['clang', '-std=c11', '-D_DARWIN_C_SOURCE', '-O1', '-g',
                    '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                    '-Dwrite=test_write', '-Dfsync=test_sync', '-Dclose=test_close',
                    '-Drename=test_rename', '-I'+str(d), '-I'+str(ROOT/'apps-ipod'),
                    str(d/'test.c'), str(ROOT/'apps-ipod/database/sound_cal.c'),
                    '-o', str(d/'test')], check=True)
    subprocess.run([str(d/'test')], cwd=d, check=True)
