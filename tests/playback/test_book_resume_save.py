"""Real book-save/event/snapshot code with failure and track-change injection.

File publication and scheduler transitions are mocked. This tests ownership and
retry decisions, not a hardware playback engine or general concurrency proof.
"""
from pathlib import Path
import os
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / "firmware-source/apps-ipod/metadata/book_resume.c").read_text()
playback = (root / "firmware-source/apps-ipod/audio/playback.c").read_text()


def function(text, name):
    start = re.search(r"^[^\n;{}]*\b" + name + r"\([^;]*?\)\n\{", text, re.M).start()
    brace = text.index("{", start)
    depth, end = 1, brace + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


def structure(name):
    start = source.index("struct " + name + "\n{")
    return source[start:source.index("};", start) + 2]


code = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define MAX_PATH 260
#define BOOK_ID_MAX 256
#define BOOK_END_SLACK_MS 10000
#define TEF_AUTO_SKIP 1
#define PLAY_STOPPED 0
enum book_left { BOOK_LEFT_PARTWAY, BOOK_LEFT_ENDED, BOOK_LEFT_FINISHED, BOOK_LEFT_UNSTARTED };
struct book_resume { uint64_t track; int index; unsigned long elapsed,offset; enum book_left left; };
struct mp3entry {
    char path[MAX_PATH], album_text[64], author_text[64], genre_text[32];
    char *album, *albumartist, *artist, *genre_string;
    unsigned long elapsed,offset,length;
    void *cuesheet;
};
struct track_event { int flags; struct mp3entry *id3; };
struct mutex { int depth; };
static struct mutex book_mutex, ended_mutex, id3_mutex;
static void mutex_lock(struct mutex *m) { m->depth++; }
static void mutex_unlock(struct mutex *m) { assert(m->depth>0); m->depth--; }
static void id3_mutex_lock(void) { mutex_lock(&id3_mutex); }
static void id3_mutex_unlock(void) { mutex_unlock(&id3_mutex); }
static struct { bool segregate_audiobooks; } global_settings;
static struct mp3entry live;
static int play_status, display_index;
static void (*lookup_hook)(void), (*rekey_hook)(void), (*rewrite_hook)(void);
static struct mp3entry *audio_current_track(void) {
    assert(id3_mutex.depth>0);
    if(lookup_hook) { void (*hook)(void)=lookup_hook; lookup_hook=NULL; hook(); }
    return &live;
}
static void copy_mp3entry(struct mp3entry *dst,const struct mp3entry *src) {
    assert(id3_mutex.depth>0); *dst=*src;
    dst->album=src->album?dst->album_text:NULL;
    dst->albumartist=src->albumartist?dst->author_text:NULL;
    dst->artist=src->artist?dst->author_text:NULL;
    dst->genre_string=src->genre_string?dst->genre_text:NULL;
}
static bool db_spoken_is_spoken_genre(const char *s) { return s && !strcmp(s,"Audiobook"); }
static void book_resume_id(char *out,size_t n,const char *album,const char *author) {
    snprintf(out,n,"%s\t%s",album,author?author:"unknown");
}
static uint64_t path_key(const char *s) {
    uint64_t h=1469598103934665603ULL;
    while(*s) { h^=(unsigned char)*s++; h*=1099511628211ULL; }
    return h;
}
static uint64_t book_resume_key(const char *s) { return path_key(s); }
static void strmemccpy(char *dst,const char *src,size_t n) { snprintf(dst,n,"%s",src); }
static int playlist_get_display_index(void) { return display_index; }
static void rekey(void) {
    assert(book_mutex.depth>0 && !ended_mutex.depth && !id3_mutex.depth);
    if(rekey_hook) { void (*hook)(void)=rekey_hook; rekey_hook=NULL; hook(); }
}
'''
code += structure("entry") + structure("book_ended_track")
code += r'''
static struct book_ended_track ended_track;
static bool ended_pending;
static unsigned ended_generation;
static struct entry written[8];
static char written_path[8][MAX_PATH];
static int rewrite_calls, fail_call;
static bool rewrite(const struct entry *e) {
    assert(book_mutex.depth>0 && !ended_mutex.depth && !id3_mutex.depth);
    int i=rewrite_calls++; assert(i<8); written[i]=*e;
    if(e->path) { snprintf(written_path[i],MAX_PATH,"%s",e->path); written[i].path=written_path[i]; }
    if(rewrite_hook) { void (*hook)(void)=rewrite_hook; rewrite_hook=NULL; hook(); }
    return rewrite_calls!=fail_call;
}
'''
code += function(playback, "audio_current_track_copy")
for name in ["book_name", "track_finish_event", "loaded_book", "acknowledge_ended", "book_resume_save"]:
    code += function(source, name)
code += r'''
static void load(const char *path,bool named) {
    memset(&live,0,sizeof(live)); snprintf(live.path,sizeof(live.path),"%s",path);
    snprintf(live.album_text,sizeof(live.album_text),"Novel");
    snprintf(live.author_text,sizeof(live.author_text),"Writer");
    snprintf(live.genre_text,sizeof(live.genre_text),"Audiobook");
    live.album=named?live.album_text:NULL; live.albumartist=live.artist=live.author_text;
    live.genre_string=live.genre_text; live.elapsed=23456; live.offset=34567; live.length=90000;
    live.cuesheet=&live; play_status=1;
}
static void setup(void) {
    assert(!book_mutex.depth && !ended_mutex.depth && !id3_mutex.depth);
    memset(&ended_track,0,sizeof(ended_track)); ended_pending=false; ended_generation=0;
    global_settings.segregate_audiobooks=true; rewrite_calls=fail_call=0;
    lookup_hook=rekey_hook=rewrite_hook=NULL; display_index=3; play_status=0;
    memset(written,0,sizeof(written));
}
static void finish(const char *path) {
    struct mp3entry id3={0}; snprintf(id3.path,sizeof(id3.path),"%s",path);
    id3.genre_string="Audiobook"; id3.elapsed=id3.length=80000;
    struct track_event te={.flags=TEF_AUTO_SKIP,.id3=&id3}; track_finish_event(0,&te);
}
static void finish_new(void) { finish("/books/new.mp3"); }
static void change_track(void) { load("/books/changed.mp3",false); live.elapsed=56789; }
static void finish_same(void) { finish("/books/one.mp3"); }
static void no_locks(void) { assert(!book_mutex.depth && !ended_mutex.depth && !id3_mutex.depth); }
int main(void) {
    int cases=0;
    /* Failed completion remains pending, then is retried and acknowledged. */
    setup(); finish("/books/one.mp3"); fail_call=1; book_resume_save();
    assert(ended_pending && rewrite_calls==1); fail_call=0; book_resume_save();
    assert(!ended_pending && rewrite_calls==2 && written[1].pos.left==BOOK_LEFT_ENDED); cases++;
    /* A new event arriving during I/O cannot be acknowledged as the old one. */
    setup(); finish("/books/one.mp3"); rewrite_hook=finish_new; book_resume_save();
    assert(ended_pending && ended_track.book==path_key("/books/new.mp3"));
    book_resume_save(); assert(!ended_pending && written[1].book==path_key("/books/new.mp3")); cases++;
    /* Snapshot path/elapsed before a rekey or the earlier book's rewrite yields. */
    setup(); load("/books/one.mp3",false); rekey_hook=change_track; book_resume_save();
    assert(rewrite_calls==1 && written[0].book==path_key("/books/one.mp3"));
    assert(!strcmp(written[0].path,"/books/one.mp3") && written[0].pos.elapsed==23456); cases++;
    setup(); finish("/books/old.mp3"); load("/books/one.mp3",false);
    rewrite_hook=change_track; book_resume_save();
    assert(rewrite_calls==2 && written[1].book==path_key("/books/one.mp3"));
    assert(!strcmp(written[1].path,"/books/one.mp3") && written[1].pos.offset==34567); cases++;
    setup(); load("/books/one.mp3",true); rekey_hook=change_track; book_resume_save();
    assert(!written[0].path && written[0].book==path_key("Novel\tWriter")); cases++;
    /* A newer same-book progress record supersedes the ended chapter only on success. */
    setup(); finish("/books/one.mp3"); load("/books/one.mp3",false);
    fail_call=1; book_resume_save(); assert(ended_pending && written[0].pos.left==BOOK_LEFT_PARTWAY);
    fail_call=0; book_resume_save(); assert(!ended_pending); cases++;
    setup(); finish("/books/one.mp3"); load("/books/one.mp3",false);
    rewrite_hook=finish_same; book_resume_save(); assert(ended_pending);
    play_status=0; book_resume_save(); assert(!ended_pending && written[1].pos.left==BOOK_LEFT_ENDED); cases++;
    setup(); load("/books/one.mp3",false); lookup_hook=finish_new; book_resume_save();
    assert(ended_pending && rewrite_calls==1); cases++;
    setup(); finish("/books/one.mp3"); global_settings.segregate_audiobooks=false;
    book_resume_save(); assert(ended_pending && !rewrite_calls); cases++;
    setup(); load("/music/song.mp3",false); strcpy(live.genre_text,"Music");
    book_resume_save(); assert(!rewrite_calls); cases++;
    setup(); struct mp3entry copy; assert(!audio_current_track_copy(&copy)); no_locks(); cases++;
    load("/books/one.mp3",true); assert(audio_current_track_copy(&copy));
    change_track(); assert(!strcmp(copy.path,"/books/one.mp3") && !strcmp(copy.album,"Novel"));
    assert(copy.elapsed==23456 && copy.cuesheet==NULL); no_locks(); cases++;
    live.path[0]=0; assert(!audio_current_track_copy(&copy)); no_locks(); cases++;
    /* Original event filters: actual end, spoken genre and feature enabled. */
    setup(); load("/books/one.mp3",false); struct track_event te={0,&live};
    track_finish_event(0,&te); assert(!ended_pending); te.flags=TEF_AUTO_SKIP;
    track_finish_event(0,&te); assert(!ended_pending); live.elapsed=live.length;
    track_finish_event(0,&te); assert(ended_pending); no_locks(); cases++;
    printf("PASS: %d actual audiobook snapshot/save/retry and event cases (ASan/UBSan)\n",cases);
}
'''
with tempfile.TemporaryDirectory(prefix="book-save-audit-") as temp:
    harness = Path(temp) / "harness.c"
    executable = Path(temp) / "harness"
    harness.write_text(code)
    subprocess.run(["clang", "-std=c11", "-O1", "-g", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                    str(harness), "-o", str(executable)], check=True)
    subprocess.run([str(executable)], check=True,
                   env={**os.environ, "UBSAN_OPTIONS": "halt_on_error=1"})
