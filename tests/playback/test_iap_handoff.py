"""Actual iAP dispatch/lifecycle and storage barrier with controlled queue/I/O.

Host-only: no device or volume access. IAP_CORE_SOURCE can point at the prior
core to demonstrate its early ACK at runtime; the current library is still used.
"""
from pathlib import Path
import os
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
lib = (root / 'firmware-source/apps-ipod/iap/iap-library.c').read_text()
core = Path(os.environ.get('IAP_CORE_SOURCE', root / 'firmware-source/apps-ipod/iap/iap-core.c')).read_text()

def function(source, name):
    start = re.search(r'^[^\n;{}]*\b' + name + r'\([^;]*?\)\n\{', source, re.M).start()
    brace = source.index('{', start)
    depth, end = 1, brace + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end] + '\n'

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
#define IF_PRIO(...)
#define IF_COP(...)
#define QPEEK_REMOVE_EVENTS 512
#define IAP_LIST_IDLE 0
#define IAP_LIST_BUSY 1
#define IAP_ART_NONE 0
#define IAP_LIBRARY_SERIAL 1
#define IAP_LIBRARY_USB 2
struct mutex { pthread_mutex_t m; };
static void mutex_init(struct mutex *m) { assert(!pthread_mutex_init(&m->m,NULL)); }
static void mutex_lock(struct mutex *m) { assert(!pthread_mutex_lock(&m->m)); }
static void mutex_unlock(struct mutex *m) { assert(!pthread_mutex_unlock(&m->m)); }
static int disable_irq_save(void) { return 0; }
static void restore_irq(int level) { (void)level; }
struct queue_event { long id; intptr_t data; };
struct event_queue { struct queue_event ev[32]; int n; bool live; };
static struct event_queue worker_q;
static bool host;
static bool usb_host_wants_storage(void) { return host; }
static jmp_buf drained;
static void (*ready_hook)(void);
static void queue_wait(struct event_queue *q,struct queue_event *ev) {
    if(!q->n) longjmp(drained,1);
    if(ready_hook) {void (*hook)(void)=ready_hook;ready_hook=NULL;hook();}
    if(ev) {*ev=q->ev[0];memmove(q->ev,q->ev+1,--q->n*sizeof(q->ev[0]));}
}
static bool queue_peek_ex(struct event_queue *q,struct queue_event *ev,unsigned flags,const long f[][2]) {
    assert(q->live);(void)flags;
    for(int i=0;i<q->n;i++) {
        if(f && (q->ev[i].id<f[0][0] || q->ev[i].id>f[0][1]))continue;
        if(ev)*ev=q->ev[i];
        memmove(q->ev+i,q->ev+i+1,(q->n-i-1)*sizeof(q->ev[0]));q->n--;return true;
    }
    return false;
}
static void queue_post(struct event_queue *q,long id,intptr_t data) {
    assert(q->live && q->n<32);q->ev[q->n++]=(struct queue_event){id,data};
}
static void queue_init(struct event_queue *q,bool registered) {
    assert(!registered);*q=(struct event_queue){.live=true};
}
static void queue_delete(struct event_queue *q) { assert(q->live);q->live=false;q->n=0; }
enum { EV_PLAY=1,EV_MIX,EV_ARTWORK,EV_PREFETCH,EV_LIST,EV_EXIT };
struct entry {int unused;};
struct block {char stack[64],art_jpeg_of[16];struct {char path[16];} art_next;};
static struct block block_store,*block;
static const uint32_t size_entries[]={0,5};
static struct {int iap_browse_size;} global_settings={1};
static int handle,claims,capacity,folder_count_seen;
static bool catalog_cached,all_songs;
static unsigned int worker_id;
static struct mutex worker_mutex,library_mutex;
static bool worker_mutex_ready;
static volatile bool building,leaving;
static volatile int lists_state,queue_state;
static uint32_t list_count;
static int lists_commit;
static struct {volatile bool cancel,prefetch_stop,prefetching,reading;int state;unsigned size,off,rd,wr;size_t len[4];} art;
static int writes,frees,allocs,resets,joins;
static int buflib_ops_locked;
static bool fail_create;
static int core_alloc_ex(size_t size,void *ops) {(void)size;(void)ops;allocs++;return 1;}
static void *core_get_data(int h) {assert(h==1);return &block_store;}
static void core_free(int h) {assert(h==1);frees++;}
static unsigned create_thread(void (*fn)(void),void *stack,size_t size,int flags,const char *name) {
    (void)fn;(void)stack;(void)size;(void)flags;(void)name;return fail_create?0:7;
}
static void iap_library_reset(void) {resets++;}
static void (*join_hook)(void);
static void worker(void);
static void thread_wait(unsigned id) {
    assert(id==7);joins++;
    if(join_hook){void (*hook)(void)=join_hook;join_hook=NULL;hook();}
    worker();
}
static void play_tracks(uint32_t x) {(void)x;writes++;}
static void play_mix(int x) {(void)x;writes++;}
static void read_artwork(intptr_t x) {(void)x;writes++;}
static void prefetch_artwork(void) {writes++;}
static void read_lists(intptr_t x) {(void)x;writes++;}
static void discard_work_state(void);
'''
for name in ['library_mutex_init','worker_lock','library_lock','worker','open_block','iap_library_claim','iap_library_close','discard_work_state','iap_library_usb_handoff']:
    code += function(lib,name)
code += r'''
static void dispatch_worker(void) { if(!setjmp(drained))worker(); }
static void reset(void) {
    library_mutex_init();host=false;block=NULL;handle=0;worker_id=0;claims=0;
    capacity=0;leaving=building=false;lists_state=queue_state=0;
    memset(&art,0,sizeof(art));worker_q=(struct event_queue){0};
    writes=frees=allocs=resets=joins=0;ready_hook=join_hook=NULL;fail_create=false;
}
static void reclaim_during_close(void) {
    assert(leaving);iap_library_claim(IAP_LIBRARY_USB);
    assert(!open_block(false));assert(!frees);
}
static void handoff_between_wakeup_and_dequeue(void) {
    host=true;iap_library_usb_handoff();
    /* Remount immediately: the worker must not replay a dequeued stale job. */
    host=false;
}
static atomic_bool barrier_done,barrier_started;
static void *barrier_thread(void *arg) {
    (void)arg;atomic_store(&barrier_started,true);iap_library_usb_handoff();
    atomic_store(&barrier_done,true);return NULL;
}
static void library_tests(void) {
    reset();host=true;assert(!open_block(false));assert(!allocs);host=false;
    assert(open_block(false));iap_library_claim(IAP_LIBRARY_SERIAL);iap_library_claim(IAP_LIBRARY_USB);
    for(int id=EV_PLAY;id<=EV_LIST;id++)queue_post(&worker_q,id,0);
    building=true;lists_state=queue_state=IAP_LIST_BUSY;
    art.prefetching=art.reading=true;art.size=40;art.len[0]=40;
    host=true;iap_library_usb_handoff();
    assert(!worker_q.n && claims==3 && block && worker_id==7 && !frees);
    assert(!building && !art.reading && !art.prefetching && !art.size && !art.len[0]);
    assert(lists_state==IAP_LIST_IDLE && queue_state==IAP_LIST_IDLE);
    assert(art.cancel && art.prefetch_stop);
    host=false;queue_post(&worker_q,EV_PLAY,0);dispatch_worker();assert(writes==1);
    /* No claim loss for a configured USB accessory. */
    iap_library_close(IAP_LIBRARY_SERIAL);assert(claims==IAP_LIBRARY_USB && !frees && worker_id==7);
    iap_library_close(IAP_LIBRARY_USB);assert(!worker_id && !block && frees==1 && joins==1);
    reset();assert(open_block(false));host=true;queue_post(&worker_q,EV_PLAY,0);dispatch_worker();assert(!writes);
    host=false;queue_post(&worker_q,EV_ARTWORK,0);queue_post(&worker_q,EV_EXIT,0);
    host=true;iap_library_usb_handoff();assert(worker_q.n==1 && worker_q.ev[0].id==EV_EXIT);worker();
    reset();assert(open_block(false));queue_post(&worker_q,EV_PLAY,0);
    ready_hook=handoff_between_wakeup_and_dequeue;dispatch_worker();assert(!writes && !worker_q.n);
    reset();assert(open_block(false));iap_library_claim(IAP_LIBRARY_SERIAL);
    join_hook=reclaim_during_close;iap_library_close(IAP_LIBRARY_SERIAL);
    assert(claims==IAP_LIBRARY_USB && !block && !leaving && frees==1);
    assert(open_block(false));assert(allocs==2);
    reset();fail_create=true;assert(!open_block(false));assert(!block && !worker_id && frees==1);
    /* A real active callback owns worker_mutex. Handoff must wait, and must
     * cancel an artwork ring producer before trying to acquire its lock. */
    reset();assert(open_block(false));host=true;worker_lock();
    atomic_store(&barrier_started,false);atomic_store(&barrier_done,false);
    pthread_t t;assert(!pthread_create(&t,NULL,barrier_thread,NULL));
    while(!atomic_load(&barrier_started))sched_yield();
    while(!art.cancel || !art.prefetch_stop)sched_yield();
    assert(!atomic_load(&barrier_done));mutex_unlock(&worker_mutex);
    assert(!pthread_join(t,NULL));assert(atomic_load(&barrier_done));
}
'''
# Compile the actual core dispatch, with calls to the real library handoff above.
code += r'''
#define IAP_EV_TICK 101
#define IAP_EV_MSG_RCVD 102
#define IAP_EV_ARTWORK 103
#define IAP_EV_RESET 104
#define IAP_EV_MALLOC 105
#define SYS_POWEROFF 106
#define SYS_REBOOT 107
#define SYS_USB_CONNECTED 108
#define SYS_USB_CONNECTED_ACK 109
static struct event_queue iap_queue;
static bool reset_pending,art_sent,iap_shutdown,iap_running=true;
static intptr_t art_seq;
static int acks,parks,packets,periods,art_stops,buffer_resets;
static struct {int state;} frame_state;
#define ST_SYNC 0
static void iap_reset_buffers(void) {buffer_resets++;}
static void iap_do_reset(void) {reset_pending=false;}
static void iap_periodic(void) {periods++;iap_library_claim(IAP_LIBRARY_SERIAL);}
static bool iap_artwork_active(void) {return false;}
static void iap_artwork_post(void) {}
static void iap_handlepkt(void) {packets++;}
static void iap_tick_stop_if_idle(void) {}
static bool iap_artwork_send_next(void) {return false;}
static void yield(void) {}
static void iap_malloc(void) {iap_running=true;}
static void iap_artwork_stop(void) {art_stops++;}
static void usb_acknowledge(long id,intptr_t seq) {
    assert(id==SYS_USB_CONNECTED_ACK && seq==99);
    /* This assertion fails against the previous core's immediate ACK. */
    assert(!worker_q.n && art.cancel && art.prefetch_stop && art_stops==1);
    acks++;
}
static void usb_wait_for_disconnect(struct event_queue *q) {
    assert(q==&iap_queue);parks++;assert(host);host=false;
}
'''
if 'static void iap_discard_packets(void)' in core:
    code += function(core,'iap_discard_packets')
code += function(core,'iap_thread')
code += r'''
static void dispatch_core(void) {if(!setjmp(drained))iap_thread();}
int main(void) {
    (void)frame_state;
    library_tests();reset();assert(open_block(false));iap_library_claim(IAP_LIBRARY_SERIAL);
    queue_post(&worker_q,EV_PLAY,0);host=true;queue_init(&iap_queue,false);
    queue_post(&iap_queue,SYS_USB_CONNECTED,99);queue_post(&iap_queue,IAP_EV_TICK,0);
    dispatch_core();assert(acks==1 && parks==1 && periods==1 && packets==1);
    assert(claims==IAP_LIBRARY_SERIAL && !frees && buffer_resets==2);
    /* Late core: skip ordinary work, but never manufacture an ACK. */
    host=true;queue_post(&iap_queue,IAP_EV_MSG_RCVD,0);queue_post(&iap_queue,IAP_EV_TICK,0);
    dispatch_core();assert(acks==1 && periods==1 && packets==1);
    host=false;queue_post(&iap_queue,IAP_EV_MSG_RCVD,0);dispatch_core();assert(packets==2);
    puts("PASS: actual iAP handoff, pending dequeue, claim/reclaim, close EXIT, artwork cancellation, late core, accessory resume and real worker barrier");
}
'''
# The IRQ receives no bytes while a host owns/pends storage, before lazy start.
receive = function(core,'iap_getc')
if not os.environ.get('IAP_CORE_SOURCE'):
    assert receive.index('usb_host_wants_storage()') < receive.index('iap_start()')
    assert '.config                  = 2' in (root/'firmware-source/firmware/usbstack/usb_iap.c').read_text()
    assert '.config = 1' in (root/'firmware-source/firmware/usbstack/usb_storage.c').read_text()
# Exercise the actual artwork producer's full-ring cancellation, not a model
# of its wait loop. The storage barrier sets the very flag sleep_hook sets.
art_code = r"""
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#define MIN(a,b) ((a)<(b)?(a):(b))
#define O_RDONLY 0
#define SEEK_SET 0
#define SEEK_END 2
#define HZ 100
#define ART_MAX 100000
#define ART_BLOCK 256
#define ART_BUFS 4
#define AA_SOURCE_NONE 0
#define AA_SOURCE_CACHE 1
#define AA_PREFER_EMBEDDED 2
#define IAP_ART_NONE 0
#define IAP_ART_FOUND 1
#define IAP_ART_FAILED 2
#define USB_LOG_IAP2_EVENT 0
#define USB_LOG_IAP2_COVER 0
static long current_tick;
static bool leaving;
static int art_track;
static struct {int kind;char path[16];off_t size,pos;} art_source;
static struct {unsigned request;bool reading,cancel;unsigned size,state,wr;size_t len[4];char buf[4][256];} art;
static struct {char art_jpeg[256];} block_store,*block=&block_store;
static int reads,closes,waits;
static int car_preference(void) {return 0;}
static bool albumart_find_source(void *track,int pref,bool exact,void *out) {
    (void)track;(void)pref;(void)exact;(void)out;
    art_source.kind=3;art_source.size=128;art_source.pos=0;return true;
}
static unsigned cache_jpeg(const char *path,bool prefetch) {(void)path;(void)prefetch;return 0;}
static int open(const char *path,int flags) {(void)path;(void)flags;return 3;}
static off_t lseek(int fd,off_t off,int whence) {(void)fd;(void)whence;return off;}
static ssize_t read(int fd,void *p,size_t n) {(void)fd;memset(p,42,n);reads++;return n;}
static int close(int fd) {assert(fd==3);closes++;return 0;}
static void sleep(int ticks) {assert(ticks==1);waits++;art.cancel=true;}
static void usb_log(int a,int b,int c,unsigned d,long e) {(void)a;(void)b;(void)c;(void)d;(void)e;}
"""
art_code += function(lib,'read_artwork')
art_code += r"""
int main(void) {
    art.request=4;art.len[0]=256;read_artwork(4);
    assert(waits==1 && !reads && closes==1 && !art.reading);
    memset(&art,0,sizeof(art));art.request=5;read_artwork(5);
    assert(reads==1 && closes==2 && art.len[0]==128 && !art.reading);
    read_artwork(4);assert(reads==1 && closes==2);
    puts("PASS: actual artwork full-ring cancellation, successful transfer and stale request rejection");
}
"""
with tempfile.TemporaryDirectory(prefix='iap-handoff-') as tmp:
    cfile=Path(tmp)/'test.c';exe=Path(tmp)/'test';cfile.write_text(code)
    subprocess.run(['clang','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-function',
                    '-fsanitize=address,undefined','-fno-omit-frame-pointer','-pthread',str(cfile),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True,env={**os.environ,'UBSAN_OPTIONS':'halt_on_error=1'},timeout=20)

    cfile.write_text(art_code)
    subprocess.run(['clang','-std=c11','-O1','-g','-Wall','-Wextra','-Werror',
                    '-fsanitize=address,undefined','-fno-omit-frame-pointer',str(cfile),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True,env={**os.environ,'UBSAN_OPTIONS':'halt_on_error=1'},timeout=20)
