from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[2]
s=(r/'firmware-source/apps-ipod/iap/iap-library.c').read_text()
a=s.index('bool iap_library_track_field(');b=s.index('bool iap_library_select(',a)
pre=r"""
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
enum{FOLDER_NONE,TYPE_TRACK,tag_title,tag_artist,tag_album,tag_genre,tag_composer,tag_length,tag_tracknumber};
static int folder=FOLDER_NONE;static unsigned list_count=2;static bool queue=false;
struct entry{int idx;};struct block{struct entry entries[2];};
static struct block storage={{{42},{7}}},*block=&storage;
static bool build(int t){return t==TYPE_TRACK;}
static bool iap_library_tracks_are_queue(void){return queue;}
static bool tagcache_entry_string(int idx,int t,char*b,size_t n){snprintf(b,n,"%d:%d",idx,t);return true;}
static bool tagcache_entry_numeric(int idx,int t,long*n){*n=idx*100+t;return true;}
static void iap_utf8_cut(char*s){(void)s;}
static int tagcache_path_slots(void){return 3;}
static bool tagcache_path_slot(int n,uint64_t*k,int*idx){int ids[]={7,99,42};*idx=ids[n];*k=1000+ids[n];return true;}
"""
main=r"""
int main(void){
 char text[32];uint64_t n;
 assert(iap_library_track_field(0,1,text,sizeof text,&n));
 assert(!strcmp(text,"42:2")); /* filtered index zero is DB slot 42, NOT zero */
 assert(iap_library_track_field(1,7,text,sizeof text,&n)&&n==1007);
 assert(iap_library_track_field(0,7,text,sizeof text,&n)&&n==1042);
 assert(iap_library_track_field(0,13,text,sizeof text,&n)&&n==4200+tag_tracknumber);
 assert(!iap_library_track_field(2,1,text,sizeof text,&n));
 assert(!iap_library_track_field(0,8,text,sizeof text,&n));
 queue=true;assert(!iap_library_track_field(0,1,text,sizeof text,&n));
 queue=false;folder=3;assert(!iap_library_track_field(0,1,text,sizeof text,&n));
 puts("PASS: real filtered metadata accessor uses selected database index, stable UID, bounds and queue/folder guards");
}
"""
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(pre+s[a:b]+main)
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True)
 subprocess.run([str(p/'t')],check=True)
