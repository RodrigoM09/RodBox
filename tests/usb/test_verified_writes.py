"""Actual USB write arm: corruption detection and exclusive buffer ownership."""
from pathlib import Path
import subprocess,tempfile
base=Path(__file__).resolve().parent
ns={'__file__':str(base/'test_write_length.py'),'__name__':'definitions'}
exec(compile((base/'test_write_length.py').read_text().split('with tempfile.TemporaryDirectory() as d:')[0],str(base/'test_write_length.py'),'exec'),ns)
h=ns['header'].replace('#define CONFIG_RTC 0','#define CONFIG_RTC 0\n#define USBSTOR_VERIFY_WRITES')
h=h.replace('#define WRITE_BUFFER_SIZE 4096', '#define WRITE_BUFFER_SIZE 24576').replace('data0[4096],data1[4096]', 'data0[24576],data1[24576]')
h=h.replace('static int writes,sends,recvs;', 'static int pending_out,reads,flushes,fault,fault_chunk;static unsigned char disk[24576],persistent[24576];\nstatic int writes,sends,recvs;')
h=h.replace('assert(ep==EP_OUT);recvs++;','assert(ep==EP_OUT);assert(!pending_out);pending_out=1;recvs++;')
h=h.replace('sends++;return 0;', 'if(csw.status==UMS_STATUS_GOOD){assert(flushes==writes);assert(!memcmp(persistent,written_data,written_count*cur_cmd.block_size));} sends++;return 0;',1)
h=h[:h.index('static int storage_write_sectors(')]+r'''
static int storage_write_sectors(sector_t sector,unsigned count,void *data){
 assert(!pending_out);writes++;written_count=count;written_sector=sector;written_data=data;
 memcpy(disk,data,count*cur_cmd.block_size);
 if(writes==fault_chunk && fault==1) disk[count*cur_cmd.block_size-1]^=1;
 return writes==fault_chunk && fault==2 ? -1 : 0;
}
static int __attribute__((unused)) storage_flush(void){
 assert(!pending_out);flushes++;
 if(writes==fault_chunk && fault==4)return -1;
 memcpy(persistent,disk,written_count*cur_cmd.block_size);return 0;
}
static int __attribute__((unused)) storage_read_sectors(sector_t sector,unsigned count,void *data){
 assert(!pending_out && sector==written_sector && count==written_count);
 /* Reads may be satisfied by volatile cache; only flush persists it. */
 assert(data!=written_data);reads++;memcpy(data,disk,count*cur_cmd.block_size);
 return writes==fault_chunk && fault==3 ? -1 : 0;
}
'''
r=ns['runner'].split('static void malformed')[0]
r=r.replace(' struct command_block_wrapper *cbw=(void*)cbw_buffer;',' if(dir==USB_DIR_OUT)pending_out=0;\n struct command_block_wrapper *cbw=(void*)cbw_buffer;')
r+=r'''
int main(void){
 for(unsigned bs=512;bs<=4096;bs*=8)for(unsigned bytes=bs;bytes<=98304;bytes+=bs)
 for(int failure=0;failure<=4;failure++)for(int chunk=1;chunk<=4;chunk++){
  memset(persistent,0,sizeof persistent);pending_out=reads=flushes=0;fault=failure;fault_chunk=chunk;reset(bytes/512);
  cur_cmd.block_size=bs;cur_cmd.count=bytes/bs;cur_cmd.data_residue=bytes;
  unsigned left=bytes,completed=0;int step=0;bool failed=false;
  while(left){
   unsigned n=MIN(left,24576u);step++;
   memset(cur_cmd.data[cur_cmd.data_select],(unsigned char)(step*17),n);
   int before=writes;transfer(USB_DIR_OUT,0,n);
   if(!failed){assert(writes==before+1);if(failure && step==chunk)failed=true;else completed+=n;}
   else assert(writes==before);
   left-=n;
   if(left)assert(state==RECEIVING_BLOCKS && pending_out && last_recv!=cbw_buffer && !sends);
  }
  assert(sends==1 && csw.status==(failed?UMS_STATUS_FAIL:UMS_STATUS_GOOD));
  assert(csw.data_residue==bytes-completed);
  assert(flushes==writes-((failure==2 && failed)?1:0));
  assert(reads==writes-(((failure==2 || failure==4) && failed)?1:0));
 }
 puts("PASS verified USB writes: 512/4096 sectors, partial/four-buffer commands, no concurrent receive/storage DMA, volatile-cache durability before GOOD, flush/write/read errors, silent corruption refusal, drain and residue");
 return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='rodbox-verified-write-') as t:
 p=Path(t);(p/'test.c').write_text(h+ns['function']('account_data_transfer')+ns['function']('receive_block_data')+ns['function']('send_csw')+r)
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
