"""Real ATA register helper + flush polling: delayed BSY and stale ready status."""
from pathlib import Path
import runpy,subprocess,tempfile,sys
base=Path(__file__).resolve().parent
extract=runpy.run_path(str(base/'test_usb_idle.py'),run_name='definitions')['extract']
source=Path(sys.argv[1]) if len(sys.argv)>1 else base.parents[1]/'firmware-source/firmware/target/arm/s5l8702/ipod6g/storage_ata-6g.c'
s=source.read_text()
header=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define BIT(x) (1u<<(x))
#define logf(...) ((void)0)
#define IS_ERR(x) ((x)<0)
#define RET_ERR(n) return -1
#define PASS_RC(e,a,b) do { int rc_=(e); if(rc_<0)return rc_; }while(0)
#define CMD_FLUSH_CACHE_EXT 0xea
#define CMD_FLUSH_CACHE 0xe7
#define USEC_TIMER (now_ns/1000)
#define TIMEOUT_EXPIRED(s,t) (USEC_TIMER-(s)>(t))
static uint32_t ATA_PIO_READY=2,ATA_PIO_CSD,ATA_PIO_DVR,ATA_PIO_DAD,ATA_PIO_DTR;
static long now_ns,issued_ns=-1,finish_delay=5400;
static unsigned error_status,delay_calls;
static bool ceata,canflush=true,ata_lba48=true;
static uint16_t identify_info[256];static uint8_t ceata_taskfile[16];
static void udelay(unsigned us){assert(us>=2);delay_calls++;if(ATA_PIO_CSD && issued_ns<0)issued_ns=now_ns;now_ns+=us*1000;}
static void yield(void){now_ns+=1000;}
static uint16_t ata_read_cbr(volatile uint32_t *reg){
 (void)reg;if(!ATA_PIO_CSD)return BIT(6);
 if(issued_ns<0)issued_ns=now_ns;
 long elapsed=now_ns-issued_ns;
 if(elapsed<400)return BIT(6); /* old READY before device asserts BSY */
 if(elapsed<finish_delay)return BIT(7);
 return BIT(6)|error_status;
}
static int ceata_wait_idle(void){return 0;}
static int ceata_write_multiple_register(int a,void*b,int c){(void)a;(void)b;(void)c;return 0;}
static int ceata_check_error(void){return 0;}
static void reset(void){ATA_PIO_CSD=ATA_PIO_DVR=ATA_PIO_DTR=0;now_ns=0;issued_ns=-1;delay_calls=error_status=0;canflush=true;memset(identify_info,0,sizeof identify_info);identify_info[83]=BIT(13);}
'''
functions='\n'.join(extract(s,n) for n in ['ata_write_cbr','ata_wait_for_not_bsy','ata_wait_for_rdy','ata_flush_cache'])
runner=r'''
int main(void){
 for(int bits=0;bits<=32;bits+=(bits?31:1)){
  reset();error_status=bits;int rc=ata_flush_cache();
  assert(issued_ns>=0 && now_ns-issued_ns>=finish_delay);
  assert((rc==0)==(bits==0));assert(delay_calls==2);
 }
 reset();finish_delay=0;assert(ata_flush_cache()==0);assert(now_ns-issued_ns>=400);
 reset();ata_write_cbr(&ATA_PIO_DTR,123);assert(ATA_PIO_DTR==123 && !delay_calls && !now_ns);
 reset();ata_write_cbr(&ATA_PIO_DVR,0x40);assert(delay_calls==1 && now_ns>=1000);
 puts("PASS ATA delayed-BSY flush: no stale-ready completion, ERR/DF preserved, instant completion supported, command/select delays only");
}
'''
with tempfile.TemporaryDirectory(prefix='rodbox-ata-settle-') as t:
 p=Path(t);(p/'test.c').write_text(header+functions+runner)
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
