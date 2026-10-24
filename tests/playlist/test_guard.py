"""Compile the actual staged add function with instrumented external services.
No audio engine or filesystem is simulated; tests exercise playlist mutation.
"""
from pathlib import Path
import subprocess,re,sys
out=Path(__file__).resolve().parent
s=(Path(sys.argv[1]) if len(sys.argv)>1 else out.parents[1]/'firmware-source/apps-ipod/playlist/playlist.c').read_text()
start=s.index('static int add_track_to_playlist_unlocked(')
end=s.index('\n/*\n * Callback for playlist_directory_tracksearch',start)
fn=s[start:end]
header=(out.parents[1]/'firmware-source/apps-ipod/playlist/playlist.h').read_text()
enums=header[header.index('enum playlist_command'):header.index('struct playlist_info')]
defines='\n'.join(line for line in s.splitlines() if re.match(r'#define PLAYLIST_(SEEK_MASK|INSERT_TYPE_|QUEUED)',line))
pre='''#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <limits.h>
struct dircache_fileref { unsigned long ref; };
struct playlist_info {
  int amount,max_playlist_size,index,first_index,last_insert_pos;
  int last_shuffled_start,control_fd,dcfrefs_handle;
  unsigned changes; bool started; unsigned long *indices;
};
static struct playlist_info current_playlist;
static struct dircache_fileref refs[32];
static int writes, init_calls, iap_calls, buffer_full;
static int logged_position, logged_command, logged_chain;
static int notify_buffer_full(void) { buffer_full++; return 0; }
static int rotate_index(struct playlist_info *p, int i) { return (i+p->amount-p->first_index)%p->amount; }
static int remove_all_tracks_unlocked(struct playlist_info *p) { p->amount=0; p->index=-1; return 0; }
static void *core_get_data(int handle) { assert(handle==1); return refs; }
static int update_control_unlocked(struct playlist_info *p,int cmd,int pos,int chain,const char *f,const char *unused,int *seek) {
  (void)p;(void)f;(void)unused;writes++;logged_position=pos;logged_command=cmd;logged_chain=chain;*seek=73;return 0;
}
static void dc_init_filerefs(struct playlist_info *p,int pos,int n) { (void)p; assert(n==1); init_calls++;refs[pos].ref=73; }
static void iap_on_tracks_count(int n) { assert(n>=0);iap_calls++; }
'''
tests='''
static unsigned long indices[32];
static void setup(bool started,int count) {
 memset(&current_playlist,0,sizeof(current_playlist));
 for(int i=0;i<32;i++) {indices[i]=100+i;refs[i].ref=1000+i;}
 current_playlist=(struct playlist_info){.amount=count,.max_playlist_size=32,.index=1,
 .first_index=0,.last_insert_pos=1,.last_shuffled_start=count,.control_fd=5,
 .dcfrefs_handle=1,.started=started,.indices=indices};
 writes=init_calls=iap_calls=buffer_full=0;
}
static void invalid(int pos,bool started) {
 setup(started,3);struct playlist_info old=current_playlist;
 unsigned long before[32];struct dircache_fileref oldrefs[32];
 memcpy(before,indices,sizeof(before));memcpy(oldrefs,refs,sizeof(refs));
 assert(add_track_to_playlist_unlocked(&current_playlist,"bad",pos,true,77)==-1);
 assert(!memcmp(&old,&current_playlist,sizeof(old)));
 assert(!memcmp(before,indices,sizeof(before)) && !memcmp(oldrefs,refs,sizeof(oldrefs)));
 assert(writes==0 && init_calls==0 && iap_calls==0);
}
int main(void) {
 int bad[]={-9,-100,INT_MIN,4,32,INT_MAX};
 for(unsigned i=0;i<sizeof(bad)/sizeof(*bad);i++) {invalid(bad[i],false);invalid(bad[i],true);}
 for(int pos=0;pos<=3;pos++) {
  setup(true,3);assert(add_track_to_playlist_unlocked(&current_playlist,"valid",pos,false,-1)==pos);
  assert(current_playlist.amount==4 && current_playlist.changes==1);
  assert(writes==1 && logged_position==pos && logged_command==PLAYLIST_COMMAND_ADD);
  assert(indices[pos]==(PLAYLIST_INSERT_TYPE_INSERT|73));assert(init_calls==1 && iap_calls==1);
  for(int i=0;i<pos;i++) assert(indices[i]==100u+i && refs[i].ref==1000u+i);
  for(int i=pos+1;i<4;i++) assert(indices[i]==99u+i && refs[i].ref==999u+i);
 }
 setup(true,3);assert(add_track_to_playlist_unlocked(&current_playlist,"queued",2,true,-1)==2);
 assert(logged_command==PLAYLIST_COMMAND_QUEUE && (indices[2]&PLAYLIST_QUEUED));
 setup(true,3);assert(add_track_to_playlist_unlocked(&current_playlist,"replay",2,true,91)==2);
 assert(writes==0 && (indices[2]&PLAYLIST_SEEK_MASK)==91 && (indices[2]&PLAYLIST_QUEUED));
 setup(false,0);assert(add_track_to_playlist_unlocked(&current_playlist,"first",PLAYLIST_INSERT,false,-1)==0);
 assert(current_playlist.last_insert_pos==-1 && current_playlist.amount==1);
 setup(true,3);current_playlist.first_index=1;
 assert(add_track_to_playlist_unlocked(&current_playlist,"rotated",PLAYLIST_INSERT_LAST_ROTATED,false,-1)==1);
 assert(current_playlist.first_index==2 && current_playlist.index==1);
 setup(true,32);assert(add_track_to_playlist_unlocked(&current_playlist,"full",32,false,-1)==-1);
 assert(buffer_full==1 && writes==0);
 puts("PASS: 12 malformed-position state-preservation cases; 4 normal insertions; queue, resume replay, empty append, rotated append, full-capacity rejection (21 cases)");
}
'''
c=out/'guard_harness.c'; c.write_text(pre+enums+defines+'\n'+fn+tests)
subprocess.run(['clang','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(c),'-o',str(out/'guard_harness')],check=True)
subprocess.run([str(out/'guard_harness')],check=True)
