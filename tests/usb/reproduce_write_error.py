"""Host-only reproducer of pending-OUT overlap after a failed disk write.

Exits 1 on the current known bug. This is not an acceptance test and never
accesses a USB device. Correct BOT error recovery is still unimplemented."""
from pathlib import Path
import tempfile,subprocess
root=Path(__file__).resolve().parents[2]
original=root/'tests/usb/test_write_length.py'
source=original.read_text().split('with tempfile.TemporaryDirectory() as d:')[0]
ns={'__file__':str(original),'__name__':'definitions'}
exec(compile(source,str(original),'exec'),ns)
header=ns['header'].replace('static int writes,sends,recvs;', 'static int writes,sends,recvs; static int pending_out,double_arm;')
header=header.replace('assert(ep==EP_OUT);recvs++;','assert(ep==EP_OUT);if(pending_out)double_arm++;pending_out=1;recvs++;')
header=header.replace('written_data=data;return 0;','written_data=data;return -1;')
runner=ns['runner'].split('int main(void){')[0]
runner=runner.replace(' struct command_block_wrapper *cbw=(void*)cbw_buffer;', ' if(dir==USB_DIR_OUT)pending_out=0;\n struct command_block_wrapper *cbw=(void*)cbw_buffer;')
runner += '''int main(void){
 pending_out=0;malformed(2,512);
 pending_out=double_arm=0;reset(16);transfer(USB_DIR_OUT,0,4096);
 assert(writes==1);
 printf("Outstanding OUT overlaps after disk error: %d; storage writes: %d; receive arms: %d\\n",double_arm,writes,recvs);
 return double_arm ? 1 : 0;
}
'''
unit=header+ns['function']('account_data_transfer')+ns['function']('receive_block_data')+ns['function']('send_csw')+runner
with tempfile.TemporaryDirectory(prefix='rodbox-usb-rearm-audit-') as t:
 p=Path(t);(p/'audit.c').write_text(unit)
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'audit.c'),'-o',str(p/'audit')],check=True)
 r=subprocess.run([str(p/'audit')],capture_output=True,text=True)
 print(r.stdout,end='');print(r.stderr,end='');raise SystemExit(r.returncode)
