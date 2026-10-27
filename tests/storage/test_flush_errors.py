"""Extract real ATA flush functions and inject hardware failures; no device access."""
from pathlib import Path
import subprocess,tempfile,re,sys
source=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[2]/'firmware-source/firmware/target/arm/s5l8702/ipod6g/storage_ata-6g.c'
s=source.read_text()
def function(name):
 m=re.search(r'^(?:static )?(?:int|void) '+name+r'\(void\)\s*\{',s,re.M);start=s.index('{',m.start());i=start+1;depth=1
 while depth:depth+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[m.start():i]
header=r'''
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#define BIT(x) (1u << (x))
#define logf(...) ((void)0)
#define IS_ERR(x) ((x)<0)
#define CMD_FLUSH_CACHE_EXT 0xea
#define CMD_FLUSH_CACHE 0xe7
static bool ceata,canflush=true,ata_lba48=true,ata_powered=true;
static unsigned short identify_info[256];
static unsigned char ceata_taskfile[16];
static int ATA_PIO_DVR,ATA_PIO_CSD,ata_mutex;
static int steps,fail_at,commands,depth,status_bits;
static void mutex_lock(int *p){(void)p;assert(depth==0);depth++;}
static void mutex_unlock(int *p){(void)p;assert(depth==1);depth--;}
static int step(void){assert(depth==1);steps++;return steps==fail_at ? -7:0;}
static int ata_wait_for_rdy(int t){(void)t;return step();}
static int ata_wait_for_not_bsy(int t){(void)t;return step();}
static void ata_write_cbr(int *r,int v){assert(depth==1);*r=v;if(r==&ATA_PIO_CSD)commands++;}
static int ata_read_cbr(int *r){(void)r;assert(depth==1);return status_bits;}
static int ceata_wait_idle(void){return step();}
static int ceata_write_multiple_register(int a,void*b,int c){(void)a;(void)b;(void)c;commands++;return step();}
static int ceata_check_error(void){return step();}
static void reset(void){ceata=false;canflush=true;ata_lba48=true;ata_powered=true;steps=fail_at=commands=depth=status_bits=0;memset(identify_info,0,sizeof(identify_info));identify_info[83]=BIT(13);}
'''
runner=r'''
int main(void){
 for(int failure=1;failure<=2;failure++){
  reset();fail_at=failure;assert(ata_flush()==-7);assert(steps==failure && !depth);assert(commands==(failure==1?0:1));
 }
 reset();assert(ata_flush()==0 && steps==2 && commands==1 && !depth && ATA_PIO_CSD==CMD_FLUSH_CACHE_EXT);
 for(int bit=0;bit<=5;bit+=5){reset();status_bits=BIT(bit);assert(ata_flush()!=0 && !depth);}
 for(int failure=1;failure<=4;failure++){
  reset();ceata=true;fail_at=failure;assert(ata_flush()==-7 && steps==failure && !depth);
 }
 reset();ceata=true;assert(ata_flush()==0 && steps==4 && commands==1 && !depth);
 reset();identify_info[83]=BIT(12);assert(ata_flush()==0 && ATA_PIO_CSD==CMD_FLUSH_CACHE);
 reset();identify_info[83]=0;identify_info[80]=BIT(5);assert(ata_flush()==0 && ATA_PIO_CSD==CMD_FLUSH_CACHE);
 reset();identify_info[83]=identify_info[80]=0;assert(ata_flush()==0 && !commands && !canflush && !depth);
 reset();canflush=false;assert(ata_flush()==0 && !commands && !steps && !depth);
 reset();ata_powered=false;assert(ata_flush()==0 && !commands && !steps && !depth);
 puts("PASS: ATA readiness, timeout, ERR/DF, CE-ATA errors, supported commands, absent capability and asleep device; balanced locks");
}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'test.c').write_text(header+function('ata_flush_cache')+function('ata_flush')+runner)
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
