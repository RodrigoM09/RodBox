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
#include "database/sound_index.h"
static void *allocation;
int core_alloc(size_t n) {assert(!allocation);allocation=calloc(1,n);return allocation?1:0;}
void *core_get_data(int h) {assert(h==1);return allocation;}
void core_pin(int h) {assert(h==1);}
void core_unpin(int h) {assert(h==1);}
void core_free(int h) {assert(h==1);free(allocation);allocation=NULL;}
uint64_t path_key_fold_hash(const char *s) {(void)s;return 0;}
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
 puts("PASS: legacy index upgrade, interrupted upgrade/resume, record identity, cache invalidation and unchanged-track reuse; ASan/UBSan");
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
        'static inline bool file_exists(const char *p){return access(p,F_OK)==0;}\n')
    (d/'core_alloc.h').write_text(
        '#include <stddef.h>\nint core_alloc(size_t);void *core_get_data(int);\n'
        'void core_pin(int);void core_unpin(int);void core_free(int);\n')
    (d/'index.c').write_text(HARNESS)
    binary = d/'index'
    subprocess.run(['clang', '-std=c11', '-D_DARWIN_C_SOURCE', '-O1', '-g',
                    '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                    '-fno-omit-frame-pointer', '-I'+str(d),
                    '-I'+str(ROOT/'apps-ipod'), str(d/'index.c'),
                    str(ROOT/'apps-ipod/database/sound_index.c'),
                    '-o', str(binary)], check=True)
    subprocess.run([str(binary)], cwd=d, check=True)
