"""Actual ATA partial-sector emulation against a byte-exact mock disk.

No device access. Reproduces stale reads and neighboring-sector rollback when
full writes overlap a cached block, plus ambiguous failed partial writes.
"""
from pathlib import Path
import argparse
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'firmware-source/firmware/drivers/ata-common.c'

PREFIX = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define MAX_PHYS_SECTOR_SIZE 4096
#define STORAGE_ALIGN_ATTR
#define MIN(a,b) ((a)<(b)?(a):(b))
#ifdef HAVE_MULTIDRIVE
#define IF_MD(...) __VA_ARGS__
#else
#define IF_MD(...)
#endif
typedef uint64_t sector_t;
static uint32_t log_sector_size;
static uint16_t phys_sector_mult;
static struct mutex { int depth; } ata_mutex;
static void mutex_lock(struct mutex *m) { assert(!m->depth); m->depth++; }
static void mutex_unlock(struct mutex *m) { assert(m->depth==1); m->depth--; }
static unsigned char disk[64*4096], expected[64*4096];
static int fail_write;
'''

SUFFIX = r'''
static int ata_transfer_sectors(uint64_t start, int count, void *buf, int write)
{
    assert(ata_mutex.depth==1 && count>0 && start+(unsigned)count<=64);
    size_t n=(size_t)count*log_sector_size;
    unsigned char *p=disk+start*log_sector_size;
    if(write && fail_write) {
        int f=fail_write; fail_write=0;
        /* A reported failure may have changed none, some, or all bytes. */
        if(f==2)memcpy(p,buf,n/2);
        if(f==3)memcpy(p,buf,n);
        return -7;
    }
    if(write)memcpy(p,buf,n); else memcpy(buf,p,n);
    return 0;
}
#define READ(s,n,b) ata_read_sectors(IF_MD(0,)s,n,b)
#define WRITE(s,n,b) ata_write_sectors(IF_MD(0,)s,n,b)
static void reset(unsigned mult, unsigned size)
{
    phys_sector_mult=mult; log_sector_size=size;
    memset(&sector_cache,0,sizeof(sector_cache));
    for(size_t i=0;i<sizeof(disk);i++)disk[i]=(unsigned char)(i*13+i/size);
    memcpy(expected,disk,sizeof(disk)); fail_write=0;
    assert(!ata_mutex.depth);
}
static uint32_t rng=0x52746319;
static uint32_t next(void){rng=rng*1664525u+1013904223u; return rng;}
int main(int argc, char **argv)
{
    const char *scenario=argc>1?argv[1]:"all";
    bool all=!strcmp(scenario,"all");
    unsigned char buf[16*4096], out[16*4096];
    for(unsigned mult=1;mult<=8;mult*=2) {
        if(all || !strcmp(scenario,"read")) {
        reset(mult,512);
        /* Prime an RMW cache through a small read, then overwrite its block. */
        assert(!READ(1,1,out));
        memset(buf,0xa9,mult*512);
        assert(!WRITE(0,mult,buf));
        assert(!READ(1,1,out));
        assert(!memcmp(out,disk+512,512));
        }

        /* A later small write must preserve the full write's other sectors. */
        if(all || !strcmp(scenario,"rollback")) {
        reset(mult,512); assert(!READ(1,1,out));
        memset(buf,0xb8,mult*512); assert(!WRITE(0,mult,buf));
        memcpy(expected,disk,sizeof(disk));
        memset(buf,0x67,512); assert(!WRITE(1,1,buf));
        memset(expected+512,0x67,512);
        assert(!memcmp(disk,expected,sizeof(disk)));
        }

        if(all || !strcmp(scenario,"failure")) {
        for(int failure=1;failure<=3;failure++) {
            reset(mult,512); assert(!READ(1,1,out));
            memset(buf,0x39,512); fail_write=failure;
            assert(WRITE(1,1,buf)<0); assert(!ata_mutex.depth);
            assert(!READ(1,1,out));
            assert(!memcmp(out,disk+512,512));
            /* A failed partial write cannot resurrect uncommitted neighbors. */
            memcpy(expected,disk,sizeof(disk));
            memset(buf,0x72,512); assert(!WRITE(2,1,buf));
            memset(expected+1024,0x72,512);
            assert(!memcmp(disk,expected,sizeof(disk)));
        }
        }

        /* Differential mixed reads/writes, leading/trailing/full blocks. */
        if(all || !strcmp(scenario,"mixed")) {
        reset(mult,512);
        for(int i=0;i<5000;i++) {
            unsigned start=next()%48, n=1+next()%16;
            if(next()&0x100) {
                for(unsigned j=0;j<n*512;j++)buf[j]=(unsigned char)next();
                assert(!WRITE(start,n,buf));
                memcpy(expected+start*512,buf,n*512);
                assert(!memcmp(disk,expected,sizeof(disk)));
            } else {
                assert(!READ(start,n,out));
                assert(!memcmp(out,expected+start*512,n*512));
            }
            assert(!ata_mutex.depth);
        }
        }
    }
    /* A native 4K logical drive does not need partial-sector emulation. */
    reset(1,4096); memset(buf,0x51,4096);
    assert(!WRITE(3,1,buf)); assert(!READ(3,1,out));
    assert(!memcmp(buf,out,4096));
    puts("PASS: full-write cache coherence, failed partial writes, 20000 mixed operations, 4K native");
}
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--scenario', choices=['all','read','rollback','failure','mixed'], default='all')
    args = parser.parse_args()
    source = args.source.read_text()
    # Copy production structs and entire read/write/cache implementation intact.
    actual = source[source.index('struct sector_cache_entry {'):
                    source.index('static int ata_get_phys_sector_mult(void)')]
    with tempfile.TemporaryDirectory(prefix='rodbox-sector-cache-') as tmp:
        d = Path(tmp)
        (d/'test.c').write_text(PREFIX+actual+SUFFIX)
        for defines in ([], ['-DHAVE_MULTIDRIVE']):
            subprocess.run(['clang','-std=gnu11','-O1','-g','-Wall','-Wextra',
                            '-Werror','-fsanitize=address,undefined',*defines,
                            str(d/'test.c'),'-o',str(d/'test')],check=True)
            subprocess.run([str(d/'test'),args.scenario],check=True)


if __name__ == '__main__':
    main()
