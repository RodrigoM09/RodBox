"""Compile the native buffered-only accessor with no playlist/tagcache fallback seams."""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
native = Path(os.environ.get(
    'RODBOX_PLAYBACK_SOURCE',
    str(root / 'firmware-source/apps-ipod/audio/playback.c')))
source = native.read_text()
start = source.index('bool audio_peek_buffered_track(')
brace = source.index('{', start)
depth, end = 1, brace + 1
while depth:
    depth += (source[end] == '{') - (source[end] == '}')
    end += 1
snapshot = source[start:end]

pre = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#define PLAY_STOPPED 0
#define PLAY_PLAYING 1
#define PLAY_PAUSED 2
struct mp3entry { char path[260]; void *cuesheet; };
struct track_info { int id3_hid; };
static int play_status, skip_offset, expected_offset;
static unsigned locks, unlocks, lock_depth, lookups, reads;
static bool buffered, metadata_ok;
static struct mp3entry metadata;
static void id3_mutex_lock(void) {
    assert(lock_depth == 0); lock_depth++; locks++;
}
static void id3_mutex_unlock(void) {
    assert(lock_depth == 1); lock_depth--; unlocks++;
}
static bool track_list_user_current(int offset, struct track_info *info) {
    assert(lock_depth == 1 && offset == expected_offset); lookups++;
    info->id3_hid = 73;
    return buffered;
}
static bool bufreadid3(int hid, struct mp3entry *out) {
    assert(lock_depth == 1 && hid == 73); reads++;
    if (!metadata_ok) return false;
    *out = metadata;
    return true;
}
/* Deliberately no audio_get_track_metadata, playlist_peek, tagcache or file I/O:
 * any such dependency in the extracted production function fails compilation. */
'''
main = r'''
static void check(bool expected, unsigned expected_lookups, unsigned expected_reads) {
    struct mp3entry out = {"unchanged", (void *)1};
    unsigned before_locks = locks, before_unlocks = unlocks;
    unsigned before_lookups = lookups, before_reads = reads;
    assert(audio_peek_buffered_track(&out, 0) == expected);
    assert(locks == before_locks + 1 && unlocks == before_unlocks + 1);
    assert(lock_depth == 0 && locks == unlocks);
    assert(lookups == before_lookups + expected_lookups);
    assert(reads == before_reads + expected_reads);
    if (expected) {
        assert(strcmp(out.path, metadata.path) == 0);
        assert(out.cuesheet == NULL);
    }
}
int main(void) {
    buffered = metadata_ok = true;
    strcpy(metadata.path, "/Music/Artist/Album/track.flac");
    metadata.cuesheet = (void *)1;
    /* A stopped engine must not even inspect a still-buffered track. */
    play_status = PLAY_STOPPED; check(false, 0, 0);
    play_status = PLAY_PLAYING; check(true, 1, 1);
    play_status = PLAY_PAUSED; check(true, 1, 1);
    /* Offset zero includes the pending skip, but never resolves it on disk. */
    play_status = PLAY_PLAYING;
    skip_offset = expected_offset = 3; check(true, 1, 1);
    buffered = false; check(false, 1, 0);
    skip_offset = expected_offset = -1; check(false, 1, 0);
    buffered = true; metadata_ok = false; check(false, 1, 1);
    metadata_ok = true; metadata.path[0] = '\0'; check(false, 1, 1);
    /* Paused misses obey the same buffered-only contract. */
    play_status = PLAY_PAUSED; check(false, 1, 1);
    buffered = false; check(false, 1, 0);
    play_status = PLAY_STOPPED; check(false, 0, 0);
    /* A later buffer fill is retriable without retaining the failed result. */
    play_status = PLAY_PLAYING; buffered = true;
    strcpy(metadata.path, "/Music/Other Artist/Other Album/next.flac");
    skip_offset = expected_offset = 0; check(true, 1, 1);
    puts("PASS: native audio_peek_buffered_track: live/paused/stopped, pending skips, unbuffered/missing/empty metadata, retry and balanced locks; no fallback dependencies");
}
'''
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory)
    (path / 'snapshot.c').write_text(pre + snapshot + main)
    subprocess.run([
        'clang', '-std=c11', '-Wall', '-Wextra', '-Werror',
        '-fsanitize=address,undefined', str(path / 'snapshot.c'),
        '-o', str(path / 'snapshot')], check=True)
    subprocess.run([str(path / 'snapshot')], check=True)
