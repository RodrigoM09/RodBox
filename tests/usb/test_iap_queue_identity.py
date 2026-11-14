"""Metadata, artwork and selection must share display-index rotation."""
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[2]
s=(r/'firmware-source/firmware/usbstack/iap/platform.c').read_text()
metadata=s[s.index('static bool get_trackinfo('):s.index('IAPBool iap_platform_get_indexed_track_info(')]
selection=s[s.index('IAPBool iap_platform_set_playing_track('):s.index('/* The library browsed from an accessory')]
s=(r/'firmware-source/apps-ipod/iap/iap-artwork.c').read_text()
art=s[s.index('static bool art_path('):s.index('/* Payload bytes a packet')]
pre=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define MAX_PATH 256
#define IAPBool bool
#define iap_true true
#define iap_false false
#define CAR_ARTWORK_OFF 0
#define AUDIO_STATUS_PLAY 1
#define check_act(c,a,...) do{if(!(c)){a;}}while(0)
struct IAPContext{int unused;};struct mp3entry{char path[MAX_PATH];};
struct playlist_track_info{const char*filename;};
static struct {int car_artwork;}global_settings={1};
static const char*paths[]={"/Music/ArtistA/AlbumA/one.flac","/Music/ArtistB/AlbumB/two.flac","/Music/ArtistC/AlbumC/three.flac"};
static int first=2,current=2,skipped=999,wps_size=-2;static bool playing=true;
static struct mp3entry id3;
static int playlist_amount(void){return 3;}
static int playlist_get_first_index(void*p){assert(!p);return first;}
static int playlist_next(int n){assert(n==0);return current;}
static int audio_status(void){return playing?1:0;}
static struct mp3entry*audio_current_track(void){snprintf(id3.path,sizeof id3.path,"%s",paths[current]);return &id3;}
static int playlist_get_track_info(void*p,int index,struct playlist_track_info*t){assert(!p);if(index<0||index>=3)return -1;t->filename=paths[index];return 0;}
static bool tagcache_fill_tags(struct mp3entry*t,const char*p){snprintf(t->path,sizeof t->path,"%s",p);return true;}
static bool get_metadata(struct mp3entry*t,int fd,const char*p){(void)t;(void)fd;(void)p;assert(0);return false;}
static void audio_skip(int n){skipped=n;}
static int art_cache_size_index(const char*s){assert(!strcmp(s,"wps"));return 1;}
static unsigned art_cache_dir_hash(const char*s){for(unsigned n=0;n<3;n++){char dir[256];snprintf(dir,sizeof dir,"%s",paths[n]);*strrchr(dir,'/')=0;if(!strcmp(dir,s))return n;}assert(0);return 99;}
static void art_cache_thumb_path(unsigned hash,int size,char*out,int len){assert(size==1);snprintf(out,len,"cache-%u",hash);}
'''
main=r'''
int main(void){struct IAPContext ctx={0};struct mp3entry tags;char path[256],expected[32];
 for(first=0;first<3;first++)for(current=0;current<3;current++)for(unsigned n=0;n<3;n++){
  unsigned raw=(n+first)%3;
  assert(get_trackinfo(n,&tags)&&!strcmp(tags.path,paths[raw]));
  assert(art_path(n,path,sizeof path));snprintf(expected,sizeof expected,"cache-%u",raw);assert(!strcmp(path,expected));
  assert(iap_platform_set_playing_track(&ctx,n));assert(skipped==(int)raw-current);
 }
 assert(!get_trackinfo(3,&tags));assert(!art_path(3,path,sizeof path));
 skipped=999;assert(!iap_platform_set_playing_track(&ctx,UINT32_MAX)&&skipped==999);
 global_settings.car_artwork=0;assert(!art_path(0,path,sizeof path));
 playing=false;assert(get_trackinfo(0,&tags));
 puts("PASS: real metadata, artwork folder identity and selected track agree for every rotated cross-artist queue position, stopped state and bounds");}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(pre+metadata+selection+art+main)
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True)
 subprocess.run([str(p/'t')],check=True)
