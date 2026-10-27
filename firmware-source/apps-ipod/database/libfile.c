/***************************************************************************
 * GNU General Public License (version 2+)
 *
 * The library's binary container; see libfile.h. The checksum is crc_32()
 * from 0xffffffff with no final inversion, over every byte after the header,
 * which is what lets an append extend it from the header's value.
 *
 * Parts, in order:
 *   - reading: libfile_open(), libfile_peek()
 *   - writing a whole file
 *   - changing a file in place: append, marks
 ****************************************************************************/

#include <stdio.h>
#include <string.h>
#include <limits.h>
#include "config.h"
#include "file.h"
#include "errno.h"
#include "crc32.h"
#include "database/libfile.h"

_Static_assert(sizeof(struct libfile_header) == 28, "libfile header layout");

#define CRC_START 0xffffffffu
#ifdef FILE_SIZE_MAX
#define LIBFILE_SIZE_MAX ((uint64_t)FILE_SIZE_MAX)
#else
#define LIBFILE_SIZE_MAX ((UINT64_C(1) << (sizeof(off_t) * CHAR_BIT - 1)) - 1)
#endif
#define LIBFILE_WRITE_MAX ((UINT64_C(1) << (sizeof(ssize_t) * CHAR_BIT - 1)) - 1)

void libfile_no_marks(struct libfile_marks *m)
{
    m->entries = -1;
    m->commitid = -1;
    m->deleted = -1;
}

/* ------------------------------------------------------------------ *
 * reading                                                            *
 * ------------------------------------------------------------------ */

static bool read_header(int fd, uint32_t magic, uint16_t version,
                        struct libfile_header *hdr)
{
    return read(fd, hdr, sizeof(*hdr)) == (ssize_t)sizeof(*hdr)
           && hdr->magic == magic && hdr->version == version;
}

/* CRC of everything from the current position to the end */
static bool crc_rest(int fd, uint32_t *crc)
{
    unsigned char buf[256];
    ssize_t n;

    *crc = CRC_START;
    while ((n = read(fd, buf, sizeof(buf))) > 0)
        *crc = crc_32(buf, n, *crc);
    return n == 0;
}

/* Whether the header's records, and nothing past them, match its checksum.
 * Only an append cut off before its header write leaves bytes past the
 * records that the checksum does not cover; a tail is always covered. */
/* 1 for a match, 0 for a mismatch, -1 for a read/seek failure. */
static int records_alone_match(int fd, const struct libfile_header *hdr)
{
    unsigned char buf[256];
    uint64_t left = (uint64_t)hdr->count * hdr->record_size;
    uint32_t crc = CRC_START;

    if (lseek(fd, sizeof(*hdr), SEEK_SET) != (off_t)sizeof(*hdr))
        return -1;
    while (left > 0)
    {
        ssize_t n = read(fd, buf, left < sizeof(buf) ? (size_t)left
                                                            : sizeof(buf));
        if (n <= 0)
            return -1;
        crc = crc_32(buf, n, crc);
        left -= n;
    }
    return crc == hdr->checksum;
}

int libfile_open(const char *path, uint32_t magic, uint16_t version,
                 uint16_t record_size, struct libfile_header *hdr,
                 uint32_t *tail)
{
    uint32_t crc;
    off_t body;
    uint64_t records;
    ssize_t n;
    int rc = LIBFILE_BAD;
    int fd = open(path, O_RDONLY);

    if (fd < 0)
        return LIBFILE_UNREAD;
    body = ffilesize(fd);
    if (body < 0)
    {
        close(fd);
        return LIBFILE_UNREAD;
    }
    body -= (off_t)sizeof(*hdr);
    n = read(fd, hdr, sizeof(*hdr));
    records = n == (ssize_t)sizeof(*hdr)
              ? (uint64_t)hdr->count * record_size : 0;
    if (n < 0 || (n < (ssize_t)sizeof(*hdr) && body >= 0))
        rc = LIBFILE_UNREAD;
    else if (n == (ssize_t)sizeof(*hdr) && hdr->magic == magic
             && hdr->version > version)
        rc = LIBFILE_NEWER;
    else if (n == (ssize_t)sizeof(*hdr) && hdr->magic == magic
             && hdr->version == version
             && hdr->record_size == record_size
             && body >= 0 && (uint64_t)body >= records)
    {
        if (!crc_rest(fd, &crc))
            rc = LIBFILE_UNREAD;
        else if (crc == hdr->checksum)
            rc = lseek(fd, sizeof(*hdr), SEEK_SET) == (off_t)sizeof(*hdr)
                 ? fd : LIBFILE_UNREAD;
        else if ((uint64_t)body > records)
        {
            int match = records_alone_match(fd, hdr);
            if (match < 0)
                rc = LIBFILE_UNREAD;
            else if (match > 0)
            {
                /* A torn append: the records stand and the rest is not there */
                body = (off_t)records; /* Bounded by the file's length. */
                rc = lseek(fd, sizeof(*hdr), SEEK_SET) == (off_t)sizeof(*hdr)
                     ? fd : LIBFILE_UNREAD;
            }
        }
    }
    if (rc != fd)
    {
        close(fd);
        return rc;
    }
    if (tail)
        *tail = (uint64_t)body - records;
    return fd;
}

bool libfile_peek(const char *path, uint32_t magic, uint16_t version,
                  struct libfile_header *hdr)
{
    int fd = open(path, O_RDONLY);
    bool ok;

    if (fd < 0)
        return false;
    ok = read_header(fd, magic, version, hdr);
    close(fd);
    return ok;
}

/* ------------------------------------------------------------------ *
 * writing a whole file                                               *
 * ------------------------------------------------------------------ */

bool libfile_begin(struct libfile_writer *w, const char *path,
                   uint32_t magic, uint16_t version, uint16_t record_size,
                   const struct libfile_marks *marks)
{
    w->fd = -1;
    w->failed = false;
    w->bytes = sizeof(w->hdr);
    memset(&w->hdr, 0, sizeof(w->hdr));
    w->hdr.magic = magic;
    w->hdr.version = version;
    w->hdr.record_size = record_size;
    w->hdr.checksum = CRC_START;
    if (marks)
        w->hdr.marks = *marks;
    else
        libfile_no_marks(&w->hdr.marks);

    int len = snprintf(w->path, sizeof(w->path), "%s.new", path);
    if (len < 0 || (size_t)len >= sizeof(w->path)) {
        w->failed = true;
        return false;
    }
    w->fd = open(w->path, O_WRONLY | O_CREAT | O_TRUNC, 0666);
    if (w->fd < 0)
        return false;
    /* A placeholder until the count and checksum are known */
    if (write(w->fd, &w->hdr, sizeof(w->hdr)) != (ssize_t)sizeof(w->hdr))
    {
        libfile_finish(w, false);
        return false;
    }
    return true;
}

bool libfile_write(struct libfile_writer *w, const void *data, size_t size,
                   uint32_t records)
{
    if (w->fd < 0 || w->failed)
        return false;
    if (records > UINT32_MAX - w->hdr.count ||
        (uint64_t)records * w->hdr.record_size > size ||
        size > LIBFILE_WRITE_MAX || w->bytes > LIBFILE_SIZE_MAX ||
        size > LIBFILE_SIZE_MAX - w->bytes ||
        write(w->fd, data, size) != (ssize_t)size) {
        w->failed = true;
        return false;
    }
    w->hdr.checksum = crc_32(data, size, w->hdr.checksum);
    w->hdr.count += records;
    w->bytes += size;
    return true;
}

bool libfile_finish(struct libfile_writer *w, bool ok)
{
    if (w->fd < 0)
        return false;
    ok = ok && !w->failed;
    if (ok)
        ok = lseek(w->fd, 0, SEEK_SET) == 0
             && write(w->fd, &w->hdr, sizeof(w->hdr))
                == (ssize_t)sizeof(w->hdr);
    /* Never replace the last good file after a failed cache flush/close. */
    if (ok && fsync(w->fd) < 0)
        ok = false;
    if (close(w->fd) < 0)
        ok = false;
    w->fd = -1;

    if (ok)
    {
        char path[MAX_PATH];
        size_t len = strlen(w->path) - 4;   /* less ".new" */

        memcpy(path, w->path, len);
        path[len] = '\0';
        ok = rename(w->path, path) == 0;
    }
    if (!ok)
        remove(w->path);
    return ok;
}

/* ------------------------------------------------------------------ *
 * changing a file in place                                           *
 * ------------------------------------------------------------------ */

bool libfile_append(const char *path, uint32_t magic, uint16_t version,
                    uint16_t record_size, const void *records, uint32_t n)
{
    struct libfile_header hdr = {0}, previous;
    if (record_size == 0 || n > SIZE_MAX / record_size)
        return false;
    size_t size = (size_t)n * record_size;
    if (size > LIBFILE_WRITE_MAX)
        return false;
    off_t end;
    uint64_t records_end;
    bool ok;
    int fd = open(path, O_RDWR);

    /* Created only when absent: any other failure leaves the file alone
     * rather than replacing it with these records. */
    if (fd < 0)
    {
        struct libfile_writer w;

        if (errno != ENOENT)
            return false;
        return libfile_begin(&w, path, magic, version, record_size, NULL)
               && libfile_finish(&w, libfile_write(&w, records, size, n));
    }

    end = ffilesize(fd);
    ok = read_header(fd, magic, version, &hdr)
         && hdr.record_size == record_size
         && n <= UINT32_MAX - hdr.count;
    previous = hdr;
    records_end = sizeof(hdr) + (uint64_t)hdr.count * record_size;
    if (ok && end >= 0 && (uint64_t)end > records_end
        && records_alone_match(fd, &hdr) == 1)
    {
        /* What a torn append left past the records goes first */
        end = (off_t)records_end; /* Bounded by the file's length above. */
        ok = ftruncate(fd, end) == 0;
    }
    ok = ok && end >= 0 && (uint64_t)end == records_end
         && records_end <= LIBFILE_SIZE_MAX
         && size <= LIBFILE_SIZE_MAX - records_end
         && lseek(fd, 0, SEEK_END) == end;
    if (ok && write(fd, records, size) != (ssize_t)size)
    {
        ftruncate(fd, end);
        ok = false;
    }
    if (ok)
    {
        hdr.count += n;
        hdr.checksum = crc_32(records, size, hdr.checksum);
        ok = lseek(fd, 0, SEEK_SET) == 0
             && write(fd, &hdr, sizeof(hdr)) == (ssize_t)sizeof(hdr);
        /* The old header's count and checksum describe the old end. */
        if (!ok) {
            /* A short header write may already have replaced count/CRC.
             * Truncating alone cannot restore the last readable header. */
            if (lseek(fd, 0, SEEK_SET) == 0)
                write(fd, &previous, sizeof(previous));
            ftruncate(fd, end);
            fsync(fd);
        }
    }
    if (ok && fsync(fd) < 0)
        ok = false;
    if (close(fd) < 0)
        ok = false;
    return ok;
}

bool libfile_set_marks(const char *path, uint32_t magic, uint16_t version,
                       const struct libfile_marks *marks)
{
    struct libfile_header hdr, previous;
    bool ok;
    int fd = open(path, O_RDWR);

    if (fd < 0)
        return false;
    ok = read_header(fd, magic, version, &hdr);
    if (ok)
    {
        previous = hdr;
        hdr.marks = *marks;
        ok = lseek(fd, 0, SEEK_SET) == 0
             && write(fd, &hdr, sizeof(hdr)) == (ssize_t)sizeof(hdr);
        if (!ok) {
            if (lseek(fd, 0, SEEK_SET) == 0)
                write(fd, &previous, sizeof(previous));
            fsync(fd);
        }
    }
    if (ok && fsync(fd) < 0)
        ok = false;
    if (close(fd) < 0)
        ok = false;
    return ok;
}
