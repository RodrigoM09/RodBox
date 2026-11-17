"""Exercise the real audiobook scanner/rewrite with failures after CRC validation.

Storage and libfile publication are mocked; no player files are accessed.
The second source argument is optional, for checking an unpatched snapshot.
"""
from pathlib import Path
import os
import re
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
source = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "firmware-source/apps-ipod/metadata/book_resume.c"
s = source.read_text()


def function(name):
    start = re.search(r"static bool " + name + r"\([^;]*?\)\n\{", s).start()
    brace = s.index("{", start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (s[end] == "{") - (s[end] == "}")
        end += 1
    return s[start:end]


def structure(name):
    start = s.index("struct " + name + "\n{")
    return s[start:s.index("};", start) + 2]


prefix = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#define MAX_PATH 260
#define ARRAYLEN(a) (sizeof(a) / sizeof((a)[0]))
#define BOOK_RESUME_FILE "positions"
#define BOOK_RESUME_MAX 3
#define LIB_BOOKS_MAGIC 1
#define LIB_BOOKS_VERSION 2
#define LIBFILE_BAD -2
#define LIBFILE_NEWER -3
enum book_left { BOOK_LEFT_PARTWAY, BOOK_LEFT_ENDED,
                 BOOK_LEFT_FINISHED, BOOK_LEFT_UNSTARTED };
struct book_resume { uint64_t track; int index; unsigned long elapsed, offset;
                     enum book_left left; };
struct libfile_header { uint32_t count; };
struct libfile_writer { int unused; };
const char *const left_words[] = { "partway", "ended", "finished", "unstarted" };
static unsigned writes;
static unsigned char original[2048], pending[2048], published[2048];
static size_t original_size, cursor, pending_size, published_size;
static uint32_t declared_size;
static int read_call, fail_call, short_call, close_calls, publish_calls;
static bool close_failure;
static int libfile_open(const char *p, unsigned m, unsigned v, unsigned r,
                        struct libfile_header *h, void *tail) {
    (void)p; (void)m; (void)v; (void)r; (void)tail;
    h->count = declared_size; cursor = 0; return 7;
}
static ssize_t mock_read(int fd, void *out, size_t n) {
    assert(fd == 7); read_call++;
    if (read_call == fail_call) return -1;
    if (read_call == short_call && n) n--;
    if (n > original_size - cursor) n = original_size - cursor;
    memcpy(out, original + cursor, n); cursor += n; return (ssize_t)n;
}
static int mock_close(int fd) {
    assert(fd == 7); close_calls++; return close_failure ? -1 : 0;
}
static int mock_rename(const char *a, const char *b) { (void)a; (void)b; return -1; }
static bool file_exists(const char *p) { (void)p; return true; }
static bool libfile_begin(struct libfile_writer *w, const char *p,
                          unsigned m, unsigned v, unsigned r, void *marks) {
    (void)w; (void)p; (void)m; (void)v; (void)r; (void)marks;
    pending_size = 0; return true;
}
static bool libfile_write(struct libfile_writer *w, const void *p, size_t n,
                          unsigned count) {
    (void)w; assert(n == count); assert(pending_size + n <= sizeof(pending));
    if (n) memcpy(pending + pending_size, p, n);
    pending_size += n; return true;
}
static bool libfile_finish(struct libfile_writer *w, bool ok) {
    (void)w;
    if (ok) { memcpy(published, pending, pending_size);
              published_size = pending_size; publish_calls++; }
    return ok;
}
#define read mock_read
#define close mock_close
#define rename mock_rename
'''

tests = r'''
static void add_record(uint64_t book, const char *path) {
    struct book_rec r = { .book=book, .track=book+10, .elapsed=1234,
                         .left=BOOK_LEFT_PARTWAY, .path_len=path ? strlen(path) : 0 };
    memcpy(original + original_size, &r, sizeof(r)); original_size += sizeof(r);
    if (r.path_len) { memcpy(original + original_size, path, r.path_len);
                     original_size += r.path_len; }
}
static void setup(void) {
    original_size=cursor=pending_size=published_size=0;
    read_call=fail_call=short_call=close_calls=publish_calls=0;
    close_failure=false; writes=0;
    add_record(1, "/books/one.mp3"); add_record(2, NULL); add_record(3, NULL);
    declared_size=original_size;
    memcpy(published, original, original_size); published_size=original_size;
}
static struct entry replacement(void) {
    return (struct entry){ .book=1, .path="/books/one.mp3",
        .pos={ .track=11, .elapsed=9999, .left=BOOK_LEFT_PARTWAY } };
}
static void preserved(void) {
    struct entry e=replacement();
    assert(!rewrite(&e)); assert(publish_calls==0); assert(close_calls==1);
    assert(published_size==original_size);
    assert(memcmp(published, original, original_size)==0);
}
static bool visit(const struct entry *e, void *data) {
    (void)e; (*(int *)data)++; return true;
}
static bool first(const struct entry *e, void *data) {
    (void)e; (*(int *)data)++; return false;
}
int main(void) {
    int cases=0;
    setup(); struct entry e=replacement(); assert(rewrite(&e));
    assert(publish_calls==1 && published_size==original_size); cases++;
    /* Read failure/short-read at every nonempty record or path request. */
    const int calls[]={1,2,3,5};
    for (unsigned i=0;i<ARRAYLEN(calls);i++) {
        setup(); fail_call=calls[i]; preserved(); cases++;
        setup(); short_call=calls[i]; preserved(); cases++;
    }
    setup(); close_failure=true; preserved(); cases++;
    setup(); declared_size=sizeof(struct book_rec)-1; preserved(); cases++;
    setup(); declared_size=sizeof(struct book_rec)+1; preserved(); cases++;
    setup(); declared_size++; preserved(); cases++;
    setup(); ((struct book_rec *)original)->left=99;
    memcpy(published,original,original_size); preserved(); cases++;
    setup(); ((struct book_rec *)original)->path_len=MAX_PATH;
    memcpy(published,original,original_size); preserved(); cases++;
    setup(); int seen=0; assert(scan(first,&seen)); assert(seen==1); cases++;
    /* The declared payload bounds the scanner, including a torn-append tail. */
    setup(); memset(original+original_size,0xa5,7); original_size+=7;
    seen=0; assert(scan(visit,&seen)); assert(seen==3); cases++;
    /* The size cap deliberately stops a successful copy, never a read error. */
    setup(); add_record(4,NULL); declared_size=original_size;
    e=replacement(); assert(rewrite(&e));
    assert(published_size < original_size && publish_calls==1); cases++;
    printf("PASS: %d actual audiobook scan/rewrite cases; failed reads preserve saved positions\n",cases);
}
'''

code = prefix + structure("book_rec") + structure("entry")
code += function("scan") + function("write_entry") + structure("copy_ctx")
code += function("copy_one") + function("rewrite") + tests
with tempfile.TemporaryDirectory(prefix="book-resume-audit-") as temp:
    harness = Path(temp) / "harness.c"
    executable = Path(temp) / "harness"
    harness.write_text(code)
    subprocess.run(["clang", "-std=c11", "-O1", "-g", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                    str(harness), "-o", str(executable)], check=True)
    subprocess.run([str(executable)], check=True,
                   env={**os.environ, "UBSAN_OPTIONS": "halt_on_error=1"})
