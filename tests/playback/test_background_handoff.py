"""Actual background dispatch/quiesce functions with host mutex and mock I/O.

No devices are used. The worker callbacks stand for writes and cleanup; real
pthread locking verifies that accepted shutdown waits for an active callback.
"""
from pathlib import Path
import os
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / "firmware-source/apps-ipod/system/bg_task.c").read_text()
header = (root / "firmware-source/apps-ipod/system/bg_task.h").read_text()


def function(name):
    start = re.search(r"^[^\n;{}]*\b" + name + r"\([^;]*?\)\n\{", source, re.M).start()
    brace = source.index("{", start)
    depth, end = 1, brace + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


def declaration(kind, name):
    start = header.index(kind + " " + name + "\n{")
    return header[start:header.index("};", start) + 2]


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
#define BG_TICK_PERIOD 500
#define BG_RETRY_DELAY 1500
#define BG_MAX_PREEMPT_FAILS 3
#define DEBUG_LOG_TASKS 0
static void debug_log(int id,const char *fmt,...) { (void)id;(void)fmt; }
struct mutex { pthread_mutex_t lock; };
static void mutex_lock(struct mutex *m) { assert(!pthread_mutex_lock(&m->lock)); }
static void mutex_unlock(struct mutex *m) { assert(!pthread_mutex_unlock(&m->lock)); }
struct queue_event { long id; intptr_t data; };
struct event_queue { int unused; };
'''
code += declaration("struct", "bg_marks") + declaration("enum", "bg_result") + declaration("struct", "bg_task")
code += r'''
static struct mutex bg_work_mutex={PTHREAD_MUTEX_INITIALIZER};
static volatile bool bg_quiescing;
static bool bg_started=true, host, pending_stop, preempted;
static struct event_queue bg_queue;
static struct bg_task *bg_tasks[4], *bg_steps[2];
static int bg_tasks_count, bg_steps_count, writes, purges, forgets, stale_reads, acks, parks, requests;
static long current_tick;
static int bg_task_preempted(const struct bg_task *t) { (void)t; return preempted; }
static bool usb_host_wants_storage(void) { return host; }
static bool queue_peek_ex(struct event_queue *q,void *ev,int n,const long ranges[][2]) {
    (void)q;(void)ev;(void)n;(void)ranges; return pending_stop;
}
static bool bg_task_stale(struct bg_task *t) { (void)t;stale_reads++;return true; }
static void bg_task_forget(struct bg_task *t) { (void)t;forgets++;writes++; }
static void bg_marks_none(struct bg_marks *m) { memset(m,0xff,sizeof(*m)); }
static struct queue_event events[8];
static int event_count, event_pos;
static jmp_buf drained;
static void queue_wait_w_tmo(struct event_queue *q,struct queue_event *ev,int delay) {
    (void)q;(void)delay;
    if(event_pos==event_count) longjmp(drained,1);
    *ev=events[event_pos++];
}
static void usb_acknowledge(long id,intptr_t seq) { (void)id;(void)seq;acks++; }
static void usb_wait_for_disconnect(struct event_queue *q) { (void)q;parks++; }
'''
for name in ["bg_task_should_stop", "bg_task_tick", "bg_thread", "bg_task_shutdown"]:
    code += function(name)
code += r'''
static enum bg_result run(void) { writes++;return BG_DONE; }
static void marks(const struct bg_marks *m) { (void)m;writes++; }
static void purge(void) { writes++;purges++; }
static void event(const struct queue_event *e) { (void)e;writes++; }
static void step(void) { writes++; }
static void request(bool rebuild) { (void)rebuild;requests++; }
static void stop_mid_pass(void) { bg_task_shutdown(false); }
static enum bg_result run_and_stop(void) { stop_mid_pass();return BG_INTERRUPTED; }
static struct bg_task ranked, stepped;
static void reset(void) {
    bg_quiescing=false;bg_started=true;host=pending_stop=preempted=false;
    writes=purges=forgets=stale_reads=acks=parks=requests=event_count=event_pos=0;
    ranked=(struct bg_task){.run=run,.purge=purge,.write_marks=marks,.handle_event=event};
    stepped=(struct bg_task){.request=request,.tick=step};
    bg_tasks[0]=&ranked;bg_tasks_count=1;bg_steps[0]=&stepped;bg_steps_count=1;
}
static void dispatch(void) { if(!setjmp(drained)) bg_thread(); }
static atomic_bool shutdown_returned;
static void *shutdown_waiter(void *p) {
    (void)p;bg_task_shutdown(true);atomic_store(&shutdown_returned,true);return NULL;
}
int main(void) {
    int cases=0;
    reset();ranked.rebuild_req=true;host=true;bg_task_tick(&ranked);
    assert(!writes && !stale_reads && ranked.rebuild_req);cases++;
    reset();ranked.update_req=true;bg_quiescing=true;bg_task_tick(&ranked);
    assert(!writes && !stale_reads && ranked.update_req);cases++;
    reset();ranked.rebuild_req=true;bg_task_tick(&ranked);
    assert(writes==4 && purges==1 && forgets==1);cases++;
    reset();bg_quiescing=true;assert(bg_task_should_stop(&ranked));cases++;
    reset();host=true;assert(bg_task_should_stop(&ranked));cases++;
    reset();pending_stop=true;assert(bg_task_should_stop(&ranked));cases++;
    reset();bg_task_shutdown(false);
    events[event_count++]=(struct queue_event){SYS_POWEROFF,0};
    events[event_count++]=(struct queue_event){SYS_TIMEOUT,0};
    events[event_count++]=(struct queue_event){1,(intptr_t)&ranked};dispatch();
    assert(!writes && !stale_reads);cases++;
    reset();ranked.run=run_and_stop;events[event_count++]=(struct queue_event){SYS_TIMEOUT,0};
    dispatch();assert(!writes && bg_quiescing);cases++;
    /* A canceled shutdown never called bg_task_shutdown: a broadcast alone
     * must not permanently disable maintenance. */
    reset();events[event_count++]=(struct queue_event){SYS_POWEROFF,0};
    events[event_count++]=(struct queue_event){SYS_TIMEOUT,0};dispatch();
    assert(writes==3 && !bg_quiescing);cases++;
    reset();bg_task_shutdown(false);events[event_count++]=(struct queue_event){SYS_USB_CONNECTED,9};
    dispatch();assert(acks==1 && parks==1 && !writes);cases++;
    reset();bg_started=false;bg_task_shutdown(true);assert(bg_quiescing);cases++;
    /* Real mutex: graceful shutdown cannot return while I/O owns the worker. */
    reset();atomic_store(&shutdown_returned,false);mutex_lock(&bg_work_mutex);
    pthread_t thread;assert(!pthread_create(&thread,NULL,shutdown_waiter,NULL));
    while(!bg_quiescing) sched_yield();
    assert(!atomic_load(&shutdown_returned));mutex_unlock(&bg_work_mutex);
    assert(!pthread_join(thread,NULL));assert(atomic_load(&shutdown_returned));cases++;
    printf("PASS: %d actual background handoff/quiesce cases, including real shutdown wait and canceled-shutdown recovery\n",cases);
}
'''
with tempfile.TemporaryDirectory(prefix="background-handoff-") as temp:
    harness = Path(temp) / "harness.c"
    executable = Path(temp) / "harness"
    harness.write_text(code)
    subprocess.run(["clang", "-std=c11", "-O1", "-g", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-pthread",
                    str(harness), "-o", str(executable)], check=True)
    subprocess.run([str(executable)], check=True,
                   env={**os.environ, "UBSAN_OPTIONS": "halt_on_error=1"})
