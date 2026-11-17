"""Production artwork writer, scaler bounds and reader with file-error injection."""
from pathlib import Path
import importlib.util
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('extractor', ROOT/'tests/storage/test_usb_idle.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
source = (ROOT/'firmware-source/apps-ipod/metadata/art_cache.c').read_text()
actual = '\n\n'.join(module.extract(source, name) for name in
                     ('aa_cover_dim', 'aa_write_aat', 'art_cache_load_aat'))
header = (ROOT/'firmware-source/apps-ipod/metadata/art_cache.h').read_text()
layout = re.search(r'struct art_cache_header\s*\{.*?\};', header, re.S).group()
constants = '\n'.join(re.findall(r'^#define ART_CACHE_(?:MAGIC|FORMAT_VERSION) .*$', header, re.M))
HARNESS = r'''
#include <assert.h>
#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include "metadata/art_sizes.h"
#define MAX_PATH 260
typedef uint16_t fb_data;
#define FB_DATA_SZ sizeof(fb_data)
#define RGB_UNPACK_RED(p) (((p)>>11)&31)
#define RGB_UNPACK_GREEN(p) (((p)>>5)&63)
#define RGB_UNPACK_BLUE(p) ((p)&31)
#define LCD_RGBPACK(r,g,b) (((r)<<11)|((g)<<5)|(b))
struct bitmap {int width,height;void *data;};
struct img_filter {int unused;};
struct mutex {int locked;};
static struct mutex aat_mutex;
static void mutex_lock(struct mutex *m){assert(!m->locked);m->locked=1;}
static void mutex_unlock(struct mutex *m){assert(m->locked);m->locked=0;}
static void img_filter_apply_banded(fb_data *p,int w,int h,const struct img_filter *f){(void)p;(void)w;(void)h;(void)f;}
#define AAT_BAND_MAX 8
static fb_data aat_band[AAT_BAND_MAX*ART_CACHE_MAX_DIM];
static char aa_tmp_path[MAX_PATH];
static bool aa_write_failed;
static int failure,writes,syncs,closes,renames,seeks,fail_seek;
static int checked_open(const char *p,int flags,int mode){return failure==1?-1:open(p,flags,mode);}
static ssize_t checked_write(int fd,const void *p,size_t n){writes++;return write(fd,p,((failure==2 && writes==1)||(failure==3 && writes==2))?n/2:n);}
static int checked_sync(int fd){syncs++;return failure==4?-1:fsync(fd);}
static int checked_close(int fd){closes++;int rc=close(fd);return failure==5?-1:rc;}
static int checked_rename(const char *a,const char *b){renames++;return failure==6?-1:rename(a,b);}
static off_t checked_seek(int fd,off_t offset,int whence){return ++seeks==fail_seek?-1:lseek(fd,offset,whence);}
static size_t checked_copy(char *dst,const char *src,size_t n){size_t len=strlen(src);if(n){size_t k=len<n-1?len:n-1;memcpy(dst,src,k);dst[k]=0;}return len;}
/* FORMAT */
#define open checked_open
#define write checked_write
#define fsync checked_sync
#define close checked_close
#define rename checked_rename
#define lseek checked_seek
#define strlcpy checked_copy
/* ACTUAL */
#undef open
#undef write
#undef fsync
#undef close
#undef rename
#undef lseek
static fb_data pixels[ART_CACHE_MAX_DIM*ART_CACHE_MAX_DIM],loaded[ART_CACHE_MAX_DIM*ART_CACHE_MAX_DIM];
int main(void){
 int fd,tw,th;struct bitmap bm={44,44,pixels};
 for(failure=1;failure<=6;failure++){
  fd=open("cache.aat",O_WRONLY|O_CREAT|O_TRUNC,0600);assert(fd>=0 && write(fd,"old",3)==3);close(fd);
  writes=syncs=closes=renames=0;aa_write_failed=false;
  assert(!aa_write_aat("cache.aat",&bm,1) && aa_write_failed);
  fd=open("cache.aat",O_RDONLY);char old[4]={0};assert(fd>=0 && read(fd,old,4)==3 && !strcmp(old,"old"));close(fd);
  assert(access("cache.new",F_OK)!=0 && closes==(failure!=1));
  assert(renames==(failure==6));
 }
 failure=0;
 for(int s=0;s<ART_CACHE_NUM_SIZES;s++){
  bm.width=bm.height=art_sizes[s].dim;size_t n=(size_t)bm.width*bm.height;
  for(size_t i=0;i<n;i++)pixels[i]=(fb_data)i;
  aa_write_failed=false;assert(aa_write_aat("cache.aat",&bm,s) && !aa_write_failed);
  fd=open("cache.aat",O_RDONLY);struct art_cache_header h;assert(read(fd,&h,sizeof(h))==sizeof(h));
  assert(h.width==bm.width && h.height==bm.height && h.layout==art_sizes[s].layout);
  assert(read(fd,loaded,n*sizeof(fb_data))==(ssize_t)(n*sizeof(fb_data)));char tail;assert(read(fd,&tail,1)==0);close(fd);
  for(int y=0;y<bm.height;y++)for(int x=0;x<bm.width;x++)
   assert(loaded[y*bm.width+x]==(fb_data)(h.layout==AA_COLUMNS?x*bm.width+y:y*bm.width+x));
 }
 /* Last file is the valid 300px row-major source. */
 fd=open("cache.aat",O_RDONLY);assert(fd>=0);
 bm.width=bm.height=44;bm.data=loaded;
 assert(art_cache_load_aat(fd,&bm,44*44*sizeof(fb_data),NULL)==44*44*sizeof(fb_data));
 seeks=0;fail_seek=1;assert(art_cache_load_aat(fd,&bm,sizeof(loaded),NULL)==-1);
 seeks=0;fail_seek=2;bm.width=bm.height=1;assert(art_cache_load_aat(fd,&bm,sizeof(loaded),NULL)==-1 && !aat_mutex.locked);
 fail_seek=0;bm.width=bm.height=INT_MAX;assert(art_cache_load_aat(fd,&bm,sizeof(loaded),NULL)==-1);
 bm.width=bm.height=44;assert(art_cache_load_aat(fd,&bm,-1,NULL)==-1);close(fd);
 aa_write_failed=false;bm.width=INT_MAX;assert(!aa_write_aat("cache.aat",&bm,1) && aa_write_failed);
 bm.width=44;aa_write_failed=false;assert(!aa_write_aat("x",&bm,1) && aa_write_failed);
 assert(aa_cover_dim(1000,500,44,&tw,&th) && tw==88 && th==44);
 assert(!aa_cover_dim(1,65535,300,&tw,&th));
 assert(!aa_cover_dim(1,INT_MAX,300,&tw,&th));
 assert(!aa_cover_dim(INT_MAX,1,300,&tw,&th));
 puts("PASS: artwork late-error publication; 44/128/300 byte layouts; reader seek/buffer bounds; extreme source dimensions; ASan/UBSan");
}
'''
with tempfile.TemporaryDirectory(prefix='rodbox-art-') as tmp:
    d = Path(tmp)
    (d/'test.c').write_text(HARNESS.replace('/* FORMAT */', constants+'\n'+layout).replace('/* ACTUAL */', actual))
    subprocess.run(['clang','-std=c11','-D_DARWIN_C_SOURCE','-O1','-g','-Wall','-Wextra','-Werror',
                    '-fsanitize=address,undefined','-I'+str(ROOT/'firmware-source/apps-ipod'),
                    str(d/'test.c'),'-o',str(d/'test')],check=True)
    subprocess.run([str(d/'test')],cwd=d,check=True)
