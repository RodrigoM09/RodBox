"""Actual notification/HID sender: finite controls must not starve behind clocks."""
from pathlib import Path
import ast,os,subprocess,tempfile
root=Path(__file__).resolve().parents[2];lib=root/'firmware-source/firmware/usbstack/iap/libiap'
tree=ast.parse((root/'tests/usb/test_iap_notification_starvation.py').read_text())
pre=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='pre' for t in n.targets))
pre=pre.replace('static uint32_t expected_index','static uint32_t finite3,finite4;\nstatic uint32_t expected_index')
pre=pre.replace('end-buffer==5','end-buffer>=1&&end-buffer<=5')
pre=pre.replace('unsigned type=buffer[0];','unsigned type=buffer[0];if(l==3)finite3|=1u<<type;else finite4|=1u<<type;')
path=Path(os.environ.get('RODBOX_NOTIFICATION_SOURCE',str(lib/'notification.c')))
notification='\n'.join(x for x in path.read_text().splitlines() if not x.startswith('#include'))
h=(lib/'hid.c').read_text();hid=h[h.index('struct ReportSize {'):h.index('static struct ReportSize output_report_size_table_fs')]+h[h.index('static struct ReportSize input_report_size_table_hs'):h.index('static struct ReportSize output_report_size_table_hs')]+h[h.index('IAPBool iap_notify_send_complete('):]
main=r'''
int main(void){
 struct IAPContext c={.send_buf=buffer,.hid_send_staging_buf=staging};
 uint32_t states=(1u<<IAPIPodStateType_PlayStatus)|(1u<<IAPIPodStateType_Power)|(1u<<IAPIPodStateType_ShuffleSetting)|(1u<<IAPIPodStateType_RepeatSetting);
 uint32_t extended=1u<<IAPStatusChangeNotificationType_PlaybackStatusExtended;
 c.enabled_notifications_3=states|(1u<<IAPIPodStateType_TrackTimePositionMSec);
 c.enabled_notifications_4=extended|(1u<<IAPStatusChangeNotificationType_TrackTimeOffsetMSec);
 iap_notify_play_status(&c,IAPIPodStatePlayStatus_Playing);
 iap_notify_power_state(&c,IAPIPodStatePowerState_ExternalPower,80);
 iap_notify_shuffle_state(&c,1);iap_notify_repeat_state(&c,1);
 advance(&c,60);
 assert((finite3&states)==states && "recurring PCM clocks must not starve finite play/power/shuffle/repeat");
 assert((finite4&extended)==extended && "extended play state must not starve behind either lingo clock");
 assert(clock3 && "finite priority must still allow recurring clock updates");
 assert(!(c.notifications_3&states)&&!(c.notifications_4&extended));
 /* Stopped is another finite event, with ongoing clock traffic. */
 c.enabled_notifications_4|=1u<<IAPStatusChangeNotificationType_PlaybackStopped;
 iap_notify_play_status(&c,IAPIPodStatePlayStatus_PlaybackStopped);advance(&c,30);
 assert(finite4&(1u<<IAPStatusChangeNotificationType_PlaybackStopped));
 puts("PASS: actual async HID completion delivers play/power/shuffle/repeat/stopped in both lingoes under continuous PCM clocks; clocks remain live");
}
'''.replace('IAPIPodStatePowerState_ExternalPower','IAPIPodStatePowerState_External')
with tempfile.TemporaryDirectory(prefix='pb56-fairness-') as d:
 p=Path(d);(p/'t.c').write_text(pre+notification+hid+main)
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-I',str(lib),str(p/'t.c'),'-o',str(p/'t')],check=True)
 subprocess.run([str(p/'t')],check=True)
