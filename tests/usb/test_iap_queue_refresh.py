"""Production playlist-start regression: replacement albums must invalidate cached indices."""
from pathlib import Path
import subprocess, tempfile
r=Path(__file__).resolve().parents[2]
s=(r/'firmware-source/apps-ipod/playlist/playlist.c').read_text()
a=s.index('void playlist_start('); b=s.index('\nvoid playlist_sync(',a)
pre=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
struct playlist_info { int index,amount; bool started; };
static struct playlist_info current_playlist;
static int lock,events,announced,play_calls;
static int playlist_amount(void){return current_playlist.amount;}
static void wps_playlist_percent_prepare(void){}
static void playlist_write_lock(struct playlist_info*p){assert(p==&current_playlist);lock++;}
static void playlist_write_unlock(struct playlist_info*p){assert(p==&current_playlist&&lock==1);lock--;}
static void sync_control_unlocked(struct playlist_info*p){assert(p==&current_playlist&&lock==1);}
void iap_on_tracks_count(uint32_t n){assert(!lock);events++;announced=n;}
static void audio_play(unsigned long elapsed,unsigned long offset){assert(!lock&&!elapsed&&!offset);assert(events==play_calls+1);assert(announced==current_playlist.amount);play_calls++;}
static void audio_resume(void){}
'''
main=r'''
int main(void){
 current_playlist.amount=10;playlist_start(0,0,0);
 /* Same count AND same index, but a different album/artist. */
 current_playlist.amount=10;playlist_start(0,0,0);
 current_playlist.amount=3;playlist_start(2,0,0);
 assert(events==3&&play_calls==3&&current_playlist.index==2);
 puts("PASS: each completed replacement queue announced before playback, including same-size albums and artists");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(pre+s[a:b]+main)
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True)
 subprocess.run([str(p/'t')],check=True)
