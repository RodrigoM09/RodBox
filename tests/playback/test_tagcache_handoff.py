"""Actual database worker/shutdown functions with injected jobs and host locks.

No devices are used. TC_HANDOFF_SOURCE can select the preceding source to
demonstrate its queued-work-after-shutdown failure.
"""
from pathlib import Path
import os
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = Path(os.environ.get("TC_HANDOFF_SOURCE", root /
              "firmware-source/apps-ipod/database/tagcache.c")).read_text()


def function(name):
    start = re.search(r"^[^\n;{}]*\b" + name + r"\([^;]*?\)\n\{", source, re.M).start()
    brace = source.index("{", start)
    depth, end = 1, brace + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


code = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <setjmp.h>
#include <pthread.h>
#include <stdatomic.h>
#include <sched.h>
#define HZ 100
#define SYS_EVENT (1L<<31)
#define SYS_TIMEOUT (SYS_EVENT|1)
#define SYS_USB_CONNECTED (SYS_EVENT|2)
#define SYS_USB_CONNECTED_ACK (SYS_EVENT|3)
#define SYS_POWEROFF (SYS_EVENT|4)
#define SYS_REBOOT (SYS_EVENT|5)
#define TAGCACHE_FILE_TEMP "temp"
#define DEBUG_LOG_TAGCACHE 0
#define LANG_TAGCACHE_FORCE_UPDATE 0
#define LANG_FAILED 1
#define logf(...) ((void)0)
struct mutex { pthread_mutex_t lock; };
static void mutex_lock(struct mutex *m) { assert(!pthread_mutex_lock(&m->lock)); }
static void mutex_unlock(struct mutex *m) { assert(!pthread_mutex_unlock(&m->lock)); }
struct queue_event { long id; intptr_t data; };
struct event_queue { int unused; };
'''
start = source.index("enum tagcache_queue {")
code += source[start:source.index("};", start) + 2]
code += r'''
static struct mutex tagcache_work_mutex={PTHREAD_MUTEX_INITIALIZER};
static struct mutex command_queue_mutex={PTHREAD_MUTEX_INITIALIZER};
static volatile bool tagcache_quiescing;
static bool usb_db_replaced, boot_finished=true, host, pending_stop;
static bool usb_stamp_taken, shutdown_during_usb;
static int usb_stamp, read_lock, write_lock, command_queue_ridx, command_queue_widx;
static struct { bool ramcache, ready, initialized; int queue_length; } tc_stat;
static struct { int serial; } current_tcmh;
static struct { bool tagcache_scan_on_eject, tagcache_scan_on_startup; } global_settings;
static struct event_queue tagcache_queue;
static struct queue_event events[16];
static int event_count,event_pos,ops,flushes,acks,parks,stamps,builds,commit_step,stops;
static jmp_buf drained;
static atomic_bool shutdown_returned;
static bool tagcache_prepare_shutdown(void);
static void queue_wait_w_tmo(struct event_queue *q,struct queue_event *ev,int delay) {
    (void)q;(void)delay;
    if(event_pos==event_count) longjmp(drained,1);
    *ev=events[event_pos++];
}
static void queue_post(struct event_queue *q,long id,intptr_t data) {
    (void)q; assert(event_count<16);events[event_count++]=(struct queue_event){id,data};
}
static bool queue_peek(struct event_queue *q,struct queue_event *ev) {
    (void)q;if(!pending_stop)return false;*ev=(struct queue_event){Q_STOP_SCAN,0};return true;
}
static bool queue_peek_ex(struct event_queue *q,void *ev,int n,const long ranges[][2]) {
    (void)q;(void)ev;(void)n;(void)ranges;return pending_stop;
}
static bool usb_host_wants_storage(void) { return host; }
static void cpu_boost(bool enable) { (void)enable; }
static void finish_interrupted_swap(void) { ops++; }
static bool db_file_exists(const char *p) { (void)p;ops++;return false; }
static bool commit(void) { ops++;return true; }
static void allocate_tagcache(void) { ops++; }
static void tagcache_commit_finalize(void) { ops++; }
static void run_command_queue(bool force) { if(force)flushes++;else ops++; }
static void load_ramcache(void) { ops++; }
static void import_runtime_data(bool force) { (void)force;ops++; }
static int save_runtime_data(bool force) { (void)force;ops++;return 1; }
static void splashf(int t,const char *f,...) { (void)t;(void)f; }
static const char *str(int id) { (void)id;return ""; }
static void debug_log(int id,const char *f,...) { (void)id;(void)f; }
static void remove_files(void) { ops++; }
static void remove_db_file(const char *p) { (void)p;ops++; }
static void tagcache_build(void) { ops++;builds++; }
static bool walk_checks_deletions(void) { ops++;return false; }
static void check_deleted_files(void) { ops++; }
static int db_dir_stamp(void) { stamps++;return 1; }
static bool usb_stamp_changed(void) { stamps++;return false; }
static void usb_acknowledge(long id,intptr_t seq) {
    (void)id;(void)seq;acks++;
    assert(!pthread_mutex_trylock(&tagcache_work_mutex.lock));
    assert(!pthread_mutex_unlock(&tagcache_work_mutex.lock));
}
static void usb_wait_for_disconnect(struct event_queue *q) {
    (void)q;parks++;
    if(shutdown_during_usb) assert(tagcache_prepare_shutdown());
}
static int tagcache_get_commit_step(void) { return commit_step; }
static void tagcache_stop_scan(void) { stops++;queue_post(&tagcache_queue,Q_STOP_SCAN,0); }
static void sleep(int ticks) { (void)ticks;read_lock=write_lock=0; }
'''
for name in ["check_event_queue", "check_event_queue_no_usb", "tagcache_thread",
             "tagcache_prepare_shutdown", "tagcache_shutdown"]:
    code += function(name)
code += r'''
static void reset(void) {
    tagcache_quiescing=false;usb_db_replaced=false;boot_finished=true;
    host=pending_stop=usb_stamp_taken=shutdown_during_usb=false;
    read_lock=write_lock=command_queue_ridx=command_queue_widx=0;
    tc_stat=(typeof(tc_stat)){.ramcache=true,.ready=true};
    global_settings=(typeof(global_settings)){true,true};
    event_count=event_pos=ops=flushes=acks=parks=stamps=builds=commit_step=stops=0;
}
static void dispatch(void) { if(!setjmp(drained)) tagcache_thread(); }
static void post(long id) { queue_post(&tagcache_queue,id,123); }
static void *shutdown_waiter(void *p) {
    (void)p;assert(tagcache_prepare_shutdown());atomic_store(&shutdown_returned,true);return NULL;
}
int main(void) {
    int cases=0;
    /* Stop consumed, then queued rebuild/update/import/load and boot timeout:
     * none may start after prepare has accepted shutdown. */
    reset();assert(tagcache_prepare_shutdown());
    post(Q_REBUILD);post(Q_UPDATE);post(Q_IMPORT_CHANGELOG);post(Q_RELOAD_RAMCACHE);
    post(Q_START_SCAN);post(SYS_TIMEOUT);dispatch();assert(!ops && !builds && !flushes);cases++;
    /* A busy merge rejects shutdown without disabling normal future jobs. */
    reset();commit_step=1;assert(!tagcache_prepare_shutdown());
    post(Q_UPDATE);dispatch();assert(builds==1 && !stops && !tagcache_quiescing);cases++;
    reset();post(SYS_POWEROFF);post(Q_UPDATE);dispatch();
    assert(builds==1 && !tagcache_quiescing);cases++;
    reset();assert(tagcache_prepare_shutdown());post(SYS_USB_CONNECTED);dispatch();
    assert(acks==1 && parks==1 && !ops && !flushes && !stamps);cases++;
    reset();post(SYS_USB_CONNECTED);dispatch();
    assert(acks==1 && parks==1 && flushes==1 && stamps==2);cases++;
    /* Shutdown while USB is parked neither deadlocks nor runs postdisconnect
     * database work after its barrier has returned. */
    reset();shutdown_during_usb=true;post(SYS_USB_CONNECTED);dispatch();
    assert(acks==1 && parks==1 && flushes==1 && stamps==1 && !usb_stamp_taken);cases++;
    reset();assert(tagcache_prepare_shutdown());tagcache_shutdown();assert(flushes==1);cases++;
    reset();tagcache_quiescing=true;assert(check_event_queue() && check_event_queue_no_usb());cases++;
    reset();host=true;assert(check_event_queue());cases++;
    reset();pending_stop=true;assert(check_event_queue() && check_event_queue_no_usb());cases++;
    reset();read_lock=write_lock=1;assert(tagcache_prepare_shutdown());assert(!read_lock&&!write_lock);cases++;
    /* Work between file locks is still active: shutdown must wait for the
     * operation's cleanup even while read_lock and write_lock are both zero. */
    reset();atomic_store(&shutdown_returned,false);mutex_lock(&tagcache_work_mutex);
    pthread_t thread;assert(!pthread_create(&thread,NULL,shutdown_waiter,NULL));
    while(!tagcache_quiescing)sched_yield();
    assert(!atomic_load(&shutdown_returned));mutex_unlock(&tagcache_work_mutex);
    assert(!pthread_join(thread,NULL));assert(atomic_load(&shutdown_returned));cases++;
    printf("PASS: %d actual database handoff/shutdown cases, including queued jobs, active cleanup, and USB park\n",cases);
}
'''
with tempfile.TemporaryDirectory(prefix="tagcache-handoff-") as temp:
    harness = Path(temp) / "harness.c"
    executable = Path(temp) / "harness"
    harness.write_text(code)
    subprocess.run(["clang", "-std=gnu11", "-O1", "-g", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-pthread",
                    str(harness), "-o", str(executable)], check=True)
    subprocess.run([str(executable)], check=True,
                   env={**os.environ, "UBSAN_OPTIONS": "halt_on_error=1"})
