from pathlib import Path
import subprocess,os,sys
out=Path(__file__).resolve().parent
# Reuse service instrumentation from the guard harness; both functions are
# extracted verbatim from staged copies of the active PodBox source.
h=(out/'guard_harness.c').read_text()
start=h.index('static int add_track_to_playlist_unlocked(')
pre=h[:start].replace('refs[32]','refs[65536]')
def function(filename,name):
 s=(out/filename).read_text();a=s.index('static int add_track_to_playlist_unlocked(');b=s.index('\n/*\n * Callback for playlist_directory_tracksearch',a)
 return s[a:b].replace('add_track_to_playlist_unlocked',name,1)
body=r'''
#include <time.h>
static unsigned long entries[65536];
struct result {struct playlist_info pl; unsigned long entries[32]; struct dircache_fileref refs[32]; int rc,writes,init,iap,cmd,pos,chain;};
static void setup_case(int n,bool started,bool cache,int first,int index) {
 for(int i=0;i<65536;i++) {entries[i]=100+i;refs[i].ref=1000+i;}
 current_playlist=(struct playlist_info){.amount=n,.max_playlist_size=65536,.index=index,
 .first_index=first,.last_insert_pos=-1,.last_shuffled_start=first>0?first:n,.control_fd=5,
 .dcfrefs_handle=cache,.started=started,.indices=entries};
 writes=init_calls=iap_calls=buffer_full=logged_command=logged_position=logged_chain=0;
}
static void snapshot(struct result *r,int rc) {
 memset(r,0,sizeof(*r)); r->pl=current_playlist;memcpy(r->entries,entries,sizeof(r->entries));
 memcpy(r->refs,refs,sizeof(r->refs));r->rc=rc;r->writes=writes;r->init=init_calls;r->iap=iap_calls;
 r->cmd=logged_command;r->pos=logged_position;r->chain=logged_chain;
}
static double bench(bool block,int n,int inserts,int pos) {
 setup_case(n,true,true,0,1);clock_t start=clock();
 for(int i=0;i<inserts;i++) {
  int p=pos<0?current_playlist.amount:pos;
  int rc=block?add_block(&current_playlist,"bench",p,false,73):add_loop(&current_playlist,"bench",p,false,73);
  assert(rc==p);
 }
 return (double)(clock()-start)/CLOCKS_PER_SEC;
}
int main(int argc,char **argv) {
 if(argc>1) {
  int positions[]={0,8000,-1};const char *names[]={"prepend","middle","append"};
  for(int k=0;k<3;k++) {double loop=0,block=0;for(int r=0;r<20;r++){loop+=bench(false,16000,1000,positions[k]);block+=bench(true,16000,1000,positions[k]);}
   printf("HOST bench %s 16000+1000 entries, 20 runs: loop %.6fs, block %.6fs, ratio %.2fx\n",names[k],loop,block,loop/block);}
  return 0;
 }
 (void)argv;
 unsigned seed=0x12345678;
 for(int test=0;test<50000;test++) {
  seed=1664525*seed+1013904223;int n=seed%24;
  seed=1664525*seed+1013904223;int pos=(int)(seed%(n+12))-8;
  if(pos==PLAYLIST_REPLACE)pos=n; /* remove-all stub is outside the movement change */
  bool started=(seed>>16)&1,cache=(seed>>17)&1,queue=(seed>>18)&1;
  int first=n?((seed>>20)%n):0,index=n?((seed>>24)%n):-1;
  struct result a,b;
  setup_case(n,started,cache,first,index);srand(42);
  snapshot(&a,add_loop(&current_playlist,"comparison",pos,queue,(test&1)?-1:91));
  setup_case(n,started,cache,first,index);srand(42);
  snapshot(&b,add_block(&current_playlist,"comparison",pos,queue,(test&1)?-1:91));
  assert(!memcmp(&a,&b,sizeof(a)));
 }
 puts("PASS: 50000 actual-function differential cases (indices, references, state, control-record command/position/chain, errors)");
}
'''
c=out/'compare_benchmark.c';c.write_text(pre+function('baseline-guard.c','add_loop')+function(str(Path(sys.argv[1]).resolve()) if len(sys.argv)>1 else '../../firmware-source/apps-ipod/playlist/playlist.c','add_block')+body)
common=['clang','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-function',str(c),'-o',str(out/'compare_benchmark')]
subprocess.run(common+['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer'],check=True)
subprocess.run([str(out/'compare_benchmark')],check=True,env={**os.environ,'UBSAN_OPTIONS':'halt_on_error=1'})
subprocess.run(common+['-O2'],check=True)
subprocess.run([str(out/'compare_benchmark'),'bench'],check=True)
