"""Actual ATA partial-sector emulation against a byte-exact mock disk.

No device access. Reproduces stale reads and neighboring-sector rollback when
full writes overlap a cached block, plus ambiguous failed partial writes.
"""
from pathlib import Path
import argparse
import importlib.util
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'firmware-source/firmware/drivers/ata-common.c'
spec = importlib.util.spec_from_file_location('extract', ROOT/'tests/storage/test_usb_idle.py')
extract_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extract_module)

PREFIX = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <limits.h>
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
static sector_t total_sectors = 64;
static uint16_t phys_sector_mult;
static struct mutex { int depth; } ata_mutex;
static void mutex_lock(struct mutex *m) { assert(!m->depth); m->depth++; }
static void mutex_unlock(struct mutex *m) { assert(m->depth==1); m->depth--; }
static unsigned char disk[64*4096], expected[64*4096];
static int fail_write;
static int read_failure, write_failure=-7;
static unsigned transfers;
'''

SUFFIX = r'''
static int ata_transfer_sectors(uint64_t start, int count, void *buf, int write)
{
    assert(ata_mutex.depth==1 && count>0 && start+(unsigned)count<=64);
    transfers++;
    size_t n=(size_t)count*log_sector_size;
    unsigned char *p=disk+start*log_sector_size;
    if(!write && read_failure){int rc=read_failure;read_failure=0;return rc;}
    if(write && fail_write) {
        int f=fail_write; fail_write=0;
        /* A reported failure may have changed none, some, or all bytes. */
        if(f==2)memcpy(p,buf,n/2);
        if(f==3)memcpy(p,buf,n);
        return write_failure;
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
    memcpy(expected,disk,sizeof(disk)); fail_write=read_failure=0; write_failure=-7; transfers=0;
    assert(!ata_mutex.depth);
}
static uint32_t rng=0x52746319;
static uint32_t next(void){rng=rng*1664525u+1013904223u; return rng;}
int main(int argc, char **argv)
{
    const char *scenario=argc>1?argv[1]:"all";
    bool all=!strcmp(scenario,"all");
    unsigned char buf[16*4096], out[16*4096];
    if(all || !strcmp(scenario,"resize_cache")) {
        reset(2,512);
        assert(!READ(1,1,out) && sector_cache.inuse);
        ata_set_phys_sector_mult(8);
        assert(phys_sector_mult==8 && !ata_mutex.depth);
        memset(buf,0xa6,512);assert(!WRITE(6,1,buf));
        memset(expected+6*512,0xa6,512);
        assert(!memcmp(disk,expected,sizeof(disk)));
        assert(!READ(6,1,out));
        assert(!memcmp(out,disk+6*512,512));
        /* Repeating the same geometry preserves a valid cache; a smaller
           virtual size must not reduce the existing physical requirement. */
        assert(sector_cache.inuse);ata_set_phys_sector_mult(8);
        assert(sector_cache.inuse);ata_set_phys_sector_mult(2);
        assert(phys_sector_mult==8 && sector_cache.inuse && !ata_mutex.depth);
        reset(2,512);assert(!READ(1,1,out));
        ata_set_phys_sector_mult(8);assert(!READ(6,1,out));
        assert(!memcmp(out,disk+6*512,512));
        reset(2,512);assert(!READ(1,1,out));
        ata_set_phys_sector_mult(3);
        assert(phys_sector_mult==2 && sector_cache.inuse && !ata_mutex.depth);
        ata_set_phys_sector_mult(0); /* existing default-to-maximum policy */
        assert(phys_sector_mult==8 && !sector_cache.inuse && !ata_mutex.depth);
        reset(2,512);assert(!READ(1,1,out));
        ata_set_phys_sector_mult(UINT_MAX); /* existing upper-bound clamp */
        assert(phys_sector_mult==8 && !sector_cache.inuse && !ata_mutex.depth);
        for(unsigned mult=1;mult<=8;mult*=2){
            reset(1,512);ata_set_phys_sector_mult(mult);
            assert(phys_sector_mult==mult && !ata_mutex.depth);
        }
        puts("PASS increasing physical-sector emulation reloads cache and preserves neighboring sectors");
    }
    if(all || !strcmp(scenario,"packed_errors")) {
        const int errors[]={INT_MIN,INT_MIN+1,INT_MIN+0x107,-1,-7,1,INT_MAX};
        for(unsigned i=0;i<sizeof(errors)/sizeof(errors[0]);i++){
            for(int stage=1;stage<=3;stage++){
                reset(8,512);read_failure=errors[i];
                unsigned start=stage==1?1:0,count=stage==2?8:1;
                assert(READ(start,count,out)<0 && !ata_mutex.depth && !sector_cache.inuse);
            }
            for(int stage=1;stage<=5;stage++){
                reset(8,512);memset(buf,0x49,sizeof(buf));
                unsigned start=stage<=2?1:0,count=stage==3?8:1;
                if(stage==1 || stage==4)read_failure=errors[i];
                else{fail_write=1;write_failure=errors[i];}
                assert(WRITE(start,count,buf)<0 && !ata_mutex.depth && !sector_cache.inuse);
                assert(!memcmp(disk,expected,sizeof(disk)));
            }
        }
        puts("PASS packed/high-bit and unexpected positive driver errors stay negative in all eight cache read/write stages");
    }
    if(all || !strcmp(scenario,"bounds")) {
        reset(8,512);
        memset(out,0x5a,sizeof(out));
        assert(READ(1,-1,out)<0 && WRITE(1,-1,buf)<0);
        assert(READ(UINT64_MAX,1,out)<0 && WRITE(UINT64_MAX,1,buf)<0);
        assert(READ(63,2,out)<0 && WRITE(63,2,buf)<0);
        assert(READ(65,0,out)<0 && WRITE(65,0,buf)<0);
        assert(!READ(64,0,out) && !WRITE(64,0,buf));
        assert(!READ(1,0,out) && !WRITE(1,0,buf));
        assert(!transfers && !ata_mutex.depth && !sector_cache.inuse);
        for(unsigned i=0;i<sizeof(out);i++)assert(out[i]==0x5a);
        assert(!memcmp(disk,expected,sizeof(disk)));
        puts("PASS negative, zero, end-of-disk and overflowing cache requests never touch storage/buffers");
    }
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
    parser.add_argument('--scenario', choices=['all','read','rollback','failure','mixed','bounds','packed_errors','resize_cache'], default='all')
    args = parser.parse_args()
    source = args.source.read_text()
    # Copy production structs and entire read/write/cache implementation intact.
    actual = source[source.index('struct sector_cache_entry {'):
                    source.index('static int ata_get_phys_sector_mult(void)')]
    actual += '\n' + extract_module.extract(source, 'ata_set_phys_sector_mult')
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
