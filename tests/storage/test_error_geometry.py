"""Packed ATA errors and untrusted IDENTIFY geometry under full ASan/UBSan."""
from pathlib import Path
import importlib.util
import subprocess
import tempfile
root=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('extract',root/'tests/storage/test_usb_idle.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
target=root/'firmware-source/firmware/target/arm/s5l8702/ipod6g'
errors=(target/'mmcdefs-target.h').read_text()
errors=errors[errors.index('#define BIT(x)'):errors.index('#define TIMEOUT_EXPIRED')]
geometry=m.extract((target/'storage_ata-6g.c').read_text(),'ata_get_log_sector_size')
usb_geometry=m.extract((root/'firmware-source/firmware/usbstack/usb_storage.c').read_text(),'valid_storage_geometry')
header=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define SECTOR_SIZE 512
#define MIN(a,b) ((a)<(b)?(a):(b))
#define READ_BUFFER_SIZE 65536
#define WRITE_BUFFER_SIZE 24576
typedef uint64_t sector_t;
static bool ceata;
static uint16_t identify_info[256];
static int depth;
static void mutex_unlock(int *m){assert(m==&depth && depth==1);depth--;}
'''
runner=r'''
static int forward(int rc,int bits,unsigned detail){PASS_RC(rc,bits,detail);return rc;}
static int forward_locked(int rc,int bits,unsigned detail){PASS_RC_MTX(rc,bits,detail,&depth);mutex_unlock(&depth);return rc;}
static uint32_t rng=0x5723ac11;
static uint32_t next(void){rng=rng*1664525+1013904223;return rng;}
static void check_geometry(bool expect,uint32_t bytes){
 uint32_t size=123;assert(ata_get_log_sector_size(&size)==expect);assert(size==(expect?bytes:123));
}
int main(void){
 assert(BIT(31)==UINT32_C(0x80000000));assert(ERR_RC(0)==INT32_MIN && ERR_RC(-1)==-1);
 for(int i=0;i<100000;i++){
  uint32_t raw=next();int32_t rc;memcpy(&rc,&raw,sizeof(rc));unsigned bits=next()%9,detail=next()%256;
  uint32_t expected=(raw&0x80000000u)?(uint32_t)(((uint64_t)raw<<bits)|detail)|0x80000000u:raw;
  assert((uint32_t)forward(rc,bits,detail)==expected);
  depth=1;assert((uint32_t)forward_locked(rc,bits,detail)==expected && !depth);
 }
 puts("PASS 100000 packed errors preserve exact 32-bit values and mutex release without signed shifts");
 const unsigned exponents[]={0,8,9,10,11,12,13,31,32,65535};
 ceata=true;
 for(unsigned i=0;i<sizeof(exponents)/sizeof(exponents[0]);i++){
  unsigned e=exponents[i];identify_info[106]=e;
#ifdef MAX_VARIABLE_LOG_SECTOR
  bool valid=e>=9 && e<=12;
#else
  bool valid=e==9;
#endif
  check_geometry(valid,valid?1u<<e:0);
 }
 ceata=false;identify_info[106]=0;check_geometry(true,512);
 identify_info[106]=0x5000;
 const uint32_t words[]={0,1,255,256,512,1024,2048,4096,0x80000000u,0xffffffffu};
 for(unsigned i=0;i<sizeof(words)/sizeof(words[0]);i++){
  identify_info[117]=words[i];identify_info[118]=words[i]>>16;
#ifdef MAX_VARIABLE_LOG_SECTOR
  bool valid=words[i]>=256 && words[i]<=2048;
#else
  bool valid=words[i]==256;
#endif
  check_geometry(valid,valid?words[i]*2:0);
 }
 assert(!valid_storage_geometry(0,1,100));assert(!valid_storage_geometry(32768,1,100));
 assert(!valid_storage_geometry(512,0,100));assert(!valid_storage_geometry(512,1,0));
 assert(!valid_storage_geometry(512,8,7));assert(!valid_storage_geometry(512,UINT32_MAX,UINT64_MAX));
 assert(valid_storage_geometry(512,1,1));assert(valid_storage_geometry(512,8,8));
 assert(valid_storage_geometry(4096,1,100));assert(valid_storage_geometry(24576,1,100));
 puts("PASS CE-ATA exponent, ATA word-size overflow, empty media, transfer-buffer size and USB multiplier bounds");
}
'''
with tempfile.TemporaryDirectory(prefix='rodbox-error-geometry-') as t:
    p=Path(t);(p/'test.c').write_text(header+errors+geometry+usb_geometry+runner)
    for defines in [[],['-DMAX_VARIABLE_LOG_SECTOR=4096']]:
        subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
                        *defines,str(p/'test.c'),'-o',str(p/'test')],check=True)
        subprocess.run([str(p/'test')],check=True)
