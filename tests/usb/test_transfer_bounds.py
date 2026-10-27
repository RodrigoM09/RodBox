"""Actual USB range helper, checked against 128-bit reference arithmetic."""
from pathlib import Path
import importlib.util,subprocess,tempfile,sys
root=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('extract',root/'tests/storage/test_usb_idle.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
p=Path(sys.argv[1]) if len(sys.argv)>1 else root/'firmware-source/firmware/usbstack/usb_storage.c'
fn=m.extract(p.read_text(),'set_transfer_range')
header=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <limits.h>
#include <stdio.h>
typedef uint64_t sector_t;
static struct{sector_t sector;unsigned count;}cur_cmd;
'''
runner=r'''
static uint64_t rng=0x474563d641;
static uint64_t next(void){rng=rng*6364136223846793005ULL+1;return rng;}
static void check(uint64_t s,uint32_t n,unsigned mult,uint64_t cap){
 __uint128_t start=(__uint128_t)s*mult,blocks=(__uint128_t)n*mult;
 bool expected=mult && start<=cap && blocks<=UINT_MAX && start+blocks<=cap;
 cur_cmd.sector=77;cur_cmd.count=99;
 assert(set_transfer_range(s,n,mult,cap)==expected);
 if(expected){assert(cur_cmd.sector==(uint64_t)start && cur_cmd.count==(unsigned)blocks);}
 else{assert(cur_cmd.sector==77 && cur_cmd.count==99);}
}
int main(void){
 check(1ULL<<63,1,2,100);check(UINT64_MAX,1,1,100);check(0,UINT32_MAX,8,UINT64_MAX);
 check(100,0,1,100);check(100,1,1,100);check(0,1,0,100);
 check(50,8,8,464);check(50,8,8,463);
 for(int i=0;i<100000;i++){
  uint64_t s=next(),cap=next();uint32_t n=next();unsigned mult=next()%17;
  check(s,n,mult,cap);check(s%1000,n%1000,mult,10000);
 }
 puts("PASS: USB range wrap/overflow boundaries and 200000 differential cases; rejected requests preserve state");
}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'test.c').write_text(header+fn+runner)
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
