#pragma once
#include <stdint.h>

/* [1] P.446 5.1.57 Command 0x003E: GetUIDTrackInfo */

enum IAPTrakcInfoTypeBits {
    /* mask[0] */
    IAPTrakcInfoTypeBits_Caps                   = 1 << 0,
    IAPTrakcInfoTypeBits_TrackName              = 1 << 1,
    IAPTrakcInfoTypeBits_ArtistName             = 1 << 2,
    IAPTrakcInfoTypeBits_AlbumName              = 1 << 3,
    IAPTrakcInfoTypeBits_GenreName              = 1 << 4,
    IAPTrakcInfoTypeBits_ComposerName           = 1 << 5,
    IAPTrakcInfoTypeBits_TotalTrackTimeDuration = 1 << 6,
    IAPTrakcInfoTypeBits_UniqueTrackID          = 1 << 7,
    /* mask[1] */
    IAPTrakcInfoTypeBits_ChapterCount      = 1 << 0,
    IAPTrakcInfoTypeBits_ChapterTimes      = 1 << 1,
    IAPTrakcInfoTypeBits_ChapterNames      = 1 << 2,
    IAPTrakcInfoTypeBits_Lyrics            = 1 << 3,
    IAPTrakcInfoTypeBits_Description       = 1 << 4,
    IAPTrakcInfoTypeBits_AlbumTrackIndex   = 1 << 5,
    IAPTrakcInfoTypeBits_DiscSetAlbumIndex = 1 << 6,
    IAPTrakcInfoTypeBits_PlayCount         = 1 << 7,
    /* mask[2] */
    IAPTrakcInfoTypeBits_SkipCount          = 1 << 0,
    IAPTrakcInfoTypeBits_PodcastReleaseDate = 1 << 1,
    IAPTrakcInfoTypeBits_LastPlayedDate     = 1 << 2,
    IAPTrakcInfoTypeBits_Year               = 1 << 3,
    IAPTrakcInfoTypeBits_StarRating         = 1 << 4,
    IAPTrakcInfoTypeBits_SeriesName         = 1 << 5,
    IAPTrakcInfoTypeBits_SeasonNumber       = 1 << 6,
    IAPTrakcInfoTypeBits_TrackVolumeAdjust  = 1 << 7,
    /* mask[3] */
    IAPTrakcInfoTypeBits_TrackEQPreset       = 1 << 0,
    IAPTrakcInfoTypeBits_TrackDataRate       = 1 << 1,
    IAPTrakcInfoTypeBits_BookmarkOffset      = 1 << 2,
    IAPTrakcInfoTypeBits_StartStopTimeOffset = 1 << 3,

};

struct IAPGetUIDTrackInfoPayload {
    uint8_t  uid[8];
    uint8_t mask[]; /* byte-indexed IAPTrakcInfoTypeBits, least-significant byte first */
} __attribute__((packed));

/* Index and count are big-endian. The mask is a sequence of bytes,
 * least-significant byte first, NOT an array of big-endian words.
 * Short legacy requests contain only the mask bytes they need.
 * See docs/PB35-LEXUS-PROTOCOL.md for independently checked layouts. */
struct IAPGetDBTrackInfoPayload {
    uint32_t database_index;
    uint32_t track_count;
    uint8_t mask[];
} __attribute__((packed));

/* One response per track and requested information type. Text occupies the remaining payload;
 * numeric field widths depend on information_type.
 * There is no track-count or mask field in a response. */
struct IAPRetDBTrackInfoPayload {
    uint32_t database_index;
    uint8_t information_type;
    uint8_t data[];
} __attribute__((packed));
