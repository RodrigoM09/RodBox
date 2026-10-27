"""Actual SCSI synchronize/eject arms: never eject or acknowledge a failed flush."""
from pathlib import Path
import subprocess,tempfile
s=(Path(__file__).resolve().parents[2]/'firmware-source/firmware/usbstack/usb_storage.c').read_text()
arm=s[s.index('        case SCSI_START_STOP_UNIT:'):s.index('        case SCSI_ALLOW_MEDIUM_REMOVAL:')]
header=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#define HAVE_STORAGE_FLUSH
#define logf(...) ((void)0)
#define SCSI_START_STOP_UNIT 0x1b
#define SCSI_SYNCHRONIZE_CACHE_10 0x35
#define SCSI_SYNCHRONIZE_CACHE_16 0x91
#define UMS_STATUS_FAIL 1
#define UMS_STATUS_GOOD 0
#define SENSE_MEDIUM_ERROR 3
#define ASC_WRITE_ERROR 12
#define SENSE_NOT_READY 2
#define ASC_MEDIUM_NOT_PRESENT 0x3a
static struct {unsigned char command_block[16];} command,*cbw=&command;
static struct {int sense_key,asc,ascq;}cur_sense_data;
static int flush_result,flushes,csw_status,csws,releases;
static bool ejected[1],lun_present;
static int lun;
static int storage_flush(void){flushes++;return flush_result;}
static void send_csw(int status){csw_status=status;csws++;}
static int storage_num_drives(void){return 1;}
static bool usb_exclusive_storage(void){return true;}
static void usb_storage_ejected(void){releases++;}
static void run(int opcode){switch(opcode){
'''
runner=r'''
default:assert(0);}}
int main(void){
 for(int opcode=0;opcode<3;opcode++)for(int fail=0;fail<2;fail++){
  int op=opcode==0?SCSI_START_STOP_UNIT:opcode==1?SCSI_SYNCHRONIZE_CACHE_10:SCSI_SYNCHRONIZE_CACHE_16;
  lun_present=true;ejected[0]=false;flush_result=fail?-1:0;flushes=csws=releases=0;cbw->command_block[4]=2;
  run(op);assert(flushes==1 && csws==1 && csw_status==(fail?UMS_STATUS_FAIL:UMS_STATUS_GOOD));
  assert(ejected[0]==(opcode==0 && !fail));assert(releases==(opcode==0 && !fail));
  if(fail)assert(cur_sense_data.sense_key==SENSE_MEDIUM_ERROR && cur_sense_data.asc==ASC_WRITE_ERROR);
 }
 lun_present=false;flushes=csws=0;run(SCSI_SYNCHRONIZE_CACHE_10);assert(!flushes && csws==1 && csw_status==UMS_STATUS_FAIL);
 lun_present=false;flushes=csws=0;run(SCSI_SYNCHRONIZE_CACHE_16);assert(!flushes && csws==1 && csw_status==UMS_STATUS_FAIL);
 lun_present=false;ejected[0]=true;flushes=csws=releases=0;run(SCSI_START_STOP_UNIT);
 assert(!flushes && csws==1 && csw_status==UMS_STATUS_FAIL && !releases && ejected[0]);
 puts("PASS: SYNC CACHE 10/16 and eject propagate flush errors, retain ownership on failure, reject absent media");
}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'test.c').write_text(header+arm+runner)
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
