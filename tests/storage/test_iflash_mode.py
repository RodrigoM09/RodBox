"""Actual iFlash IDENTIFY decode and storage-mode selection, with synthetic words."""
from pathlib import Path
import runpy,tempfile,subprocess
base=Path(__file__).resolve().parent;ns=runpy.run_path(str(base/'test_usb_idle.py'),run_name='definitions');extract=ns['extract'];s=ns['DEFAULT_SOURCE'].read_text()
h=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#define IS_ERR(x) ((x)<0)
static uint16_t identify_info[256];static bool ata_ssd_mode,ata_powered,generic_ssd,wake_mode;static int ata_mutex,depth,wakes,wake_result;
static void mutex_lock(int*p){(void)p;assert(!depth);depth++;}
static void mutex_unlock(int*p){(void)p;assert(depth==1);depth--;}
static bool ata_disk_isssd(void){return generic_ssd;}
static int ata_power_up(void){assert(depth==1);wakes++;wake_mode=ata_ssd_mode;if(!wake_result)ata_powered=true;return wake_result;}
static void model(const char*s){char m[40];memset(m,' ',40);size_t n=strlen(s);if(n>40)n=40;memcpy(m,s,n);for(int i=0;i<20;i++)identify_info[27+i]=(unsigned char)m[2*i]*256u+(unsigned char)m[2*i+1];}
'''
r=r'''
int main(void){
 ata_powered=true;model("iFlash-Platform iPod Adapters");assert(ata_is_iflash());ata_set_storage_mode(0);assert(ata_ssd_mode && !depth);
 ata_set_storage_mode(1);assert(!ata_ssd_mode);ata_set_storage_mode(2);assert(ata_ssd_mode);
 model("APPLE HDD");assert(!ata_is_iflash());ata_set_storage_mode(0);assert(!ata_ssd_mode);
 generic_ssd=true;ata_set_storage_mode(0);assert(ata_ssd_mode);
 generic_ssd=false;model("iFlash-Platform iPod Adapters");ata_ssd_mode=false;ata_powered=false;ata_set_storage_mode(0);assert(wakes==1 && !wake_mode && ata_ssd_mode && ata_powered && !depth);
 ata_ssd_mode=false;ata_powered=false;wake_result=-7;ata_set_storage_mode(0);assert(!ata_ssd_mode && !ata_powered && !depth);
 model("0123456789012345678901234567890123456789");assert(!ata_is_iflash());
 puts("PASS iFlash model decode, hint-free auto detection, explicit HDD/SSD overrides, ordinary HDD/SSD, old-mode wake and failed-wake preservation");
}
'''
with tempfile.TemporaryDirectory(prefix='rodbox-iflash-mode-') as t:
 p=Path(t);(p/'test.c').write_text(h+extract(s,'ata_is_iflash')+extract(s,'ata_set_storage_mode')+r)
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True);subprocess.run([str(p/'test')],check=True)
