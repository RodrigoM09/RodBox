"""Actual USB WRITE arm: fail disk writes, drain prefetched OUT, never re-arm busy OUT."""
from pathlib import Path
import subprocess,tempfile
base=Path(__file__).resolve().parent
ns={'__file__':str(base/'test_write_length.py'),'__name__':'definitions'}
exec(compile((base/'test_write_length.py').read_text().split('with tempfile.TemporaryDirectory() as d:')[0],str(base/'test_write_length.py'),'exec'),ns)
header=ns['header'].replace('static int writes,sends,recvs;', 'static int pending_out,overlaps,fault_at; static int writes,sends,recvs;')
header=header.replace('assert(ep==EP_OUT);recvs++;','assert(ep==EP_OUT);if(pending_out)overlaps++;pending_out=1;recvs++;')
header=header.replace('written_data=data;return 0;','written_data=data;return writes==fault_at ? -1 : 0;')
runner=ns['runner'].split('static void malformed')[0]
runner=runner.replace(' struct command_block_wrapper *cbw=(void*)cbw_buffer;',' if(dir==USB_DIR_OUT)pending_out=0;\n struct command_block_wrapper *cbw=(void*)cbw_buffer;')
runner+=r'''
int main(void){
 for(int sectors=18;sectors<=24;sectors+=6)for(int fault=1;fault<=3;fault++){
  pending_out=overlaps=0;fault_at=fault;reset(sectors);pending_out=1;
  unsigned left=sectors*512,good=0;
  for(int step=1;left;step++){
   unsigned n=MIN(left,4096u);
   transfer(USB_DIR_OUT,0,n);left-=n;
   if(step<fault)good+=n;
   assert(overlaps==0);
   assert(writes==MIN(step,fault));
   if(left){assert(sends==0 && state==RECEIVING_BLOCKS && last_recv!=cbw_buffer);}
  }
  assert(sends==1 && csw.status==UMS_STATUS_FAIL);
  assert(csw.data_residue==(unsigned)sectors*512-good);
  assert(cur_sense_data.sense_key==SENSE_MEDIUM_ERROR && cur_sense_data.asc==ASC_WRITE_ERROR);
  commands=0;transfer(USB_DIR_IN,0,sizeof(csw));transfer(USB_DIR_OUT,0,31);assert(commands==1);
  printf("PASS disk failure chunk %d / %d sectors: one OUT pending, drain, residue, next CBW\n",fault,sectors);
 }
 /* An unrelated/stale IN completion while receiving cannot write a buffer. */
 pending_out=overlaps=0;fault_at=0;reset(16);pending_out=1;
 transfer(USB_DIR_IN,0,4096);assert(writes==0 && sends==0 && recvs==0 && pending_out==1);
 transfer(USB_DIR_OUT,0,4096);transfer(USB_DIR_OUT,0,4096);
 assert(writes==2 && csw.status==UMS_STATUS_GOOD && !overlaps);
 puts("PASS stray IN does not write; subsequent valid double-buffered write succeeds");
 /* A failed disk write remains unprocessed even if draining later fails. */
 for(int status=-1;status<=0;status++)for(int short_length=0;short_length<=4095;short_length+=4095){
  pending_out=overlaps=0;fault_at=1;reset(24);pending_out=1;
  transfer(USB_DIR_OUT,0,4096);
  assert(writes==1 && !sends && cur_cmd.data_residue==24*512);
  transfer(USB_DIR_OUT,status,short_length);
  assert(writes==1 && sends==1 && csw.status==UMS_STATUS_FAIL);
  assert(csw.data_residue==24*512 && !overlaps);
 }
 puts("PASS short or failed drain preserves original failed-write residue");
 return 0;
}
'''
unit=header+ns['function']('account_data_transfer')+ns['function']('receive_block_data')+ns['function']('send_csw')+runner
with tempfile.TemporaryDirectory(prefix='rodbox-write-drain-') as t:
 p=Path(t);(p/'test.c').write_text(unit)
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
