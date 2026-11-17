"""Actual scan power/control functions, with controlled power and input events."""
from pathlib import Path
import subprocess, tempfile

root=Path(__file__).resolve().parents[2]
source=(root/'firmware-source/apps-ipod/screens/system/sound_scan.c').read_text()
def function(start,end):
    return source[source.index(start):source.index(end,source.index(start))]
abort=function('static bool ss_abort(void)','\n\n/** One track **/')
wait=function('static bool ss_wait_for_charger(void)','\n/* Whether a finished index')
pre=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
enum { CONTEXT_STD, TIMEOUT_NOBLOCK, ACTION_STD_OK=10, ACTION_STD_CANCEL,
 ACTION_STD_MENU, ACTION_NONE, SYS_USB_CONNECTED=20, SYS_POWEROFF, SYS_REBOOT };
#define HZ 100
static bool present, reconnect, ss_unplugged, ss_stop;
static int ss_event, action, draws;
static struct {bool talk_menu;} global_settings;
static bool power_input_present(void){return present;}
static int get_action(int c,int t){(void)c;(void)t;if(reconnect)present=true;return action;}
static void reset_poweroff_timer(void){}
static void ss_draw(const char *s){(void)s;draws++;}
static void talk_text(const char *s,bool e){(void)s;(void)e;}
static int default_event_handler(int b){return b;}
'''
tests=r'''
static void setup(void){present=false;reconnect=false;ss_stop=ss_unplugged=false;
ss_event=0;draws=0;action=ACTION_NONE;}
int main(void){
 setup();present=true;
 /* External power, independent of a charging-capability/charging-state flag. */
 assert(ss_wait_for_charger() && draws==0 && !ss_stop);
 assert(!ss_abort() && !ss_unplugged);
 setup();assert(ss_abort() && ss_unplugged && !ss_stop);
 setup();action=ACTION_STD_OK;assert(!ss_wait_for_charger() && ss_stop);
 setup();reconnect=true;assert(ss_wait_for_charger() && draws==1 && !ss_unplugged);
 setup();present=true;action=ACTION_STD_CANCEL;assert(ss_abort() && ss_stop);
 setup();present=true;action=SYS_USB_CONNECTED;assert(ss_abort() && ss_event==SYS_USB_CONNECTED);
 puts("PASS: 7 external-power, removal, reconnection, stop and USB event cases; ASan/UBSan");
}
'''
with tempfile.TemporaryDirectory(prefix='rodbox-power-') as tmp:
    p=Path(tmp);(p/'power.c').write_text(pre+abort+wait+tests)
    subprocess.run(['clang','-std=c11','-O1','-g','-Wall','-Wextra','-Werror',
                    '-fsanitize=address,undefined',str(p/'power.c'),'-o',str(p/'power')],check=True)
    subprocess.run([str(p/'power')],check=True)
