"""Actual queue removal and USB wrappers; mixed endpoints, sender order, ring wrap."""
from pathlib import Path
import importlib.util,subprocess,tempfile
root=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('extract',root/'tests/storage/test_usb_idle.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
queue=m.extract((root/'firmware-source/firmware/kernel/queue.c').read_text(),'queue_remove_event')
usb=m.extract((root/'firmware-source/firmware/usb.c').read_text(),'usb_clear_pending_transfer_completion_event')
core=m.extract((root/'firmware-source/firmware/usbstack/usb_core.c').read_text(),'usb_core_clear_endpoint_completion')
header=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
#define HAVE_EXTENDED_MESSAGING_AND_NAME
#define QUEUE_LENGTH_MASK 15u
#define USB_TRANSFER_COMPLETION 42
#define USB_NUM_ENDPOINTS 4
#define EP_NUM(x) ((x)&0x7f)
#define EP_DIR(x) (((x)&0x80)?1:0)
struct queue_event{long id;intptr_t data;};
struct queue_sender_list{intptr_t senders[16];};
struct event_queue{unsigned read,write;int cl;struct queue_sender_list *send;struct queue_event events[16];};
static struct event_queue usb_queue;
static int locked,irqs,unblocked;static intptr_t released;
static int disable_irq_save(void){assert(!irqs);irqs=1;return 0;}
static void restore_irq(int old){assert(old==0 && irqs && !locked);irqs=0;}
static void corelock_lock(int*p){(void)p;assert(irqs && !locked);locked=1;}
static void corelock_unlock(int*p){(void)p;assert(locked);locked=0;}
static void queue_do_unblock_sender(struct queue_sender_list*s,unsigned i){assert(locked && irqs);if(s){released=s->senders[i];s->senders[i]=0;}unblocked++;}
struct usb_transfer_completion_event_data{int endpoint;};
static struct{struct usb_transfer_completion_event_data completion_event;}ep_data[4][2];
'''
runner=r'''
static uint32_t rng=0x641814;
static unsigned next(void){rng=rng*1664525u+1013904223u;return rng;}
int main(void){
 for(int test=0;test<20000;test++){
  struct queue_sender_list send;struct queue_event model[16];intptr_t senders[16];unsigned n=next()%17;
  memset(&usb_queue,0,sizeof(usb_queue));memset(&send,0,sizeof(send));usb_queue.read=next();usb_queue.write=usb_queue.read+n;
  usb_queue.send=(test&1)?&send:NULL;
  for(unsigned i=0;i<n;i++){
   unsigned at=(usb_queue.read+i)&15;model[i]=(struct queue_event){next()%4,next()%4};senders[i]=100+i;
   usb_queue.events[at]=model[i];send.senders[at]=senders[i];
  }
  long id=next()%4;intptr_t data=next()%4;unsigned hit=0;while(hit<n && (model[hit].id!=id || model[hit].data!=data))hit++;
  unblocked=0;released=0;bool found=queue_remove_event(&usb_queue,id,data);assert(found==(hit<n));
  if(hit<n){assert(unblocked==1);if(usb_queue.send)assert(released==senders[hit]);for(unsigned i=hit;i+1<n;i++){model[i]=model[i+1];senders[i]=senders[i+1];}n--;}
  else assert(unblocked==0);
  assert(usb_queue.write-usb_queue.read==n && !locked && !irqs);
  for(unsigned i=0;i<n;i++){unsigned at=(usb_queue.read+i)&15;assert(usb_queue.events[at].id==model[i].id && usb_queue.events[at].data==model[i].data);if(usb_queue.send)assert(send.senders[at]==senders[i]);}
 }
 memset(&usb_queue,0,sizeof(usb_queue));usb_queue.read=UINT_MAX-2;usb_queue.write=usb_queue.read+5;
 intptr_t target=(intptr_t)&ep_data[1][1].completion_event,other=(intptr_t)&ep_data[2][0].completion_event;
 struct queue_event sequence[5]={{42,target},{42,other},{99,target},{42,target},{42,(intptr_t)&ep_data[1][0].completion_event}};
 for(unsigned i=0;i<5;i++)usb_queue.events[(usb_queue.read+i)&15]=sequence[i];
 usb_core_clear_endpoint_completion(0x81);assert(usb_queue.write-usb_queue.read==3);
 assert(usb_queue.events[usb_queue.read&15].data==other);
 assert(usb_queue.events[(usb_queue.read+1)&15].id==99);
 assert(usb_queue.events[(usb_queue.read+2)&15].data==(intptr_t)&ep_data[1][0].completion_event);
 usb_core_clear_endpoint_completion(0x88);assert(usb_queue.write-usb_queue.read==3);
 puts("PASS: 20000 queue-model cases, sender release/order, ring wrap, duplicate target completion purge and other endpoint/control preservation");
}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'test.c').write_text(header+queue+usb+core+runner)
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
