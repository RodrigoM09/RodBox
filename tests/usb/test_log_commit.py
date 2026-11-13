from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[2]
s=(r/'firmware-source/apps-ipod/system/debug_log.c').read_text();a=s.index('int debug_log_sync(');b=s.index('void debug_log_close(',a);sync=s[a:b]
s=(r/'firmware-source/apps-ipod/system/usb_log_file.c').read_text();a=s.index('void usb_log_file_write(');b=s.index('void usb_log_file_state(',a);writer=s[a:b]
pre=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <sys/types.h>
enum debug_log_id {DEBUG_LOG_USB,DEBUG_LOG_USB_AUDIO,OTHER};
enum {USB_LOG_ISO_STATE,USB_LOG_ISO_XFER,USB_LOG_ISO_ERROR,USB_LOG_ALT,USB_LOG_IAP_STREAM,USB_LOG_IAP_RATE,USB_LOG_IAP_RATES,USB_LOG_IAP_ERROR,USB_LOG_INSERT,USB_LOG_SET_CONFIG,USB_LOG_BUS_RESET};
#define USB_LOG_SIZE 8
struct usb_log_entry {int type;unsigned us;};
static int step,fail_sync,fail_trim,fail_write,closed,trimmed,syncs;
static unsigned written;
static int fsync(int fd){(void)fd;syncs++;step++;return fail_sync?-1:0;}
static off_t ffilesize(int fd){(void)fd;assert(step>0);return 96805;}
static int ftruncate(int fd,off_t n){(void)fd;assert(n==96805);trimmed++;return fail_trim?-1:0;}
static unsigned usb_log_written(void){return written;}
static unsigned usb_log_head(void){return 1;}
static int debug_log_open(int id){return id;}
static void debug_log_close(int id,int fd){(void)id;(void)fd;closed++;}
static void debug_log_lost(int id,int fd,unsigned n,void*p){(void)id;(void)fd;(void)n;(void)p;}
static bool usb_log_read(unsigned seq,struct usb_log_entry*e){(void)seq;e->type=USB_LOG_ISO_STATE;e->us=1;return true;}
static unsigned widen_us(unsigned x){return x;}
static void format_entry(void*e,unsigned t,char*b,size_t n){(void)e;(void)t;(void)n;strcpy(b,"entry");}
static int fdprintf(int fd,const char*fmt,const char*line){(void)fd;(void)fmt;(void)line;return fail_write?2:6;}
static void usb_log_set_written(unsigned n){assert(syncs>=4);written=n;}
'''
main=r'''
int main(void){
 assert(debug_log_sync(OTHER,2)==0&&trimmed==0);
 step=syncs=0;usb_log_file_write();assert(written==1&&trimmed==2&&closed==2);
 written=0;fail_sync=1;usb_log_file_write();assert(written==0);
 fail_sync=0;fail_trim=1;usb_log_file_write();assert(written==0);
 fail_trim=0;fail_write=1;usb_log_file_write();assert(written==0);
 fail_write=0;usb_log_file_write();assert(written==1);
 puts("PASS: USB log EOF reconciliation, media exclusion, failed sync/truncate/short-write retains ring, recovery commits");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(pre+sync+writer+main)
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True)
 subprocess.run([str(p/'t')],check=True)
