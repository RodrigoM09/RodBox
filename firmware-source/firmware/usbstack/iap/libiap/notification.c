#include <string.h>
#include "context.h"
#include "endian.h"
#include "iap.h"
#include "macros.h"
#include "spec/iap.h"

void iap_notify_track_time_position(struct IAPContext* ctx, uint32_t pos_ms) {
    ctx->notification_data.track_time_position_ms = pos_ms;
    ctx->notifications_3 |= 1 << IAPIPodStateType_TrackTimePositionMSec;
    ctx->notifications_3 |= 1 << IAPIPodStateType_TrackTimePositionSec;
    ctx->notifications_4 |= 1 << IAPStatusChangeNotificationType_TrackTimeOffsetMSec;
    ctx->notifications_4 |= 1 << IAPStatusChangeNotificationType_TrackTimeOffsetSec;
}

void iap_notify_track_playback_index(struct IAPContext* ctx, uint32_t index) {
    ctx->notification_data.track_playback_index = index;
    ctx->track_caps_pending = iap_true;
    ctx->notifications_3 |= 1 << IAPIPodStateType_TrackPlaybackIndex;
    ctx->notifications_4 |= 1 << IAPStatusChangeNotificationType_TrackIndex;
}

void iap_notify_track_unique_id(struct IAPContext* ctx, uint64_t id) {
    for(unsigned i = 0; i < 8; i++) {
        ctx->notification_data.track_unique_id[i] = (uint8_t)(id >> (56 - 8 * i));
    }
    ctx->notifications_4 |= 1u << IAPStatusChangeNotificationType_TrackUniqueID;
}

void iap_notify_track_caps(struct IAPContext* ctx, uint32_t caps) {
    ctx->notification_data.track_caps = caps;
    ctx->notifications_3 |= 1 << IAPIPodStateType_TrackCaps;
    ctx->notifications_4 |= 1 << IAPStatusChangeNotificationType_TrackCapsChanged;
}

void iap_notify_tracks_count(struct IAPContext* ctx, uint32_t count) {
    ctx->notification_data.tracks_count = count;
    ctx->notifications_3 |= 1 << IAPIPodStateType_PlaybackEngineContents;
    ctx->notifications_4 |= 1 << IAPStatusChangeNotificationType_PlaybackEngineContentsChanged;
}

void iap_notify_play_status(struct IAPContext* ctx, uint8_t status) {
    ctx->notification_data.play_status = status;
    ctx->notifications_3 |= 1 << IAPIPodStateType_PlayStatus;
    ctx->notifications_4 |= 1 << IAPStatusChangeNotificationType_PlaybackStatusExtended;
    if(status == IAPIPodStatePlayStatus_PlaybackStopped) {
        ctx->notifications_4 |= 1 << IAPStatusChangeNotificationType_PlaybackStopped;
    }
    /* should set Playback{FEW,REW}SeekStop, but no way to find which from EndFastForwardRewind */
}

void iap_notify_volume(struct IAPContext* ctx, uint8_t volume, IAPBool muted) {
    ctx->notification_data.volume     = volume;
    ctx->notification_data.mute_state = muted;
    ctx->notifications_3 |= 1 << IAPIPodStateType_Volume;
}

void iap_notify_power_state(struct IAPContext* ctx, uint8_t state, uint8_t battery_level) {
    ctx->notification_data.power_state   = state;
    ctx->notification_data.battery_level = battery_level;
    ctx->notifications_3 |= 1 << IAPIPodStateType_Power;
}

void iap_notify_shuffle_state(struct IAPContext* ctx, uint8_t state) {
    ctx->notification_data.shuffle_state = state;
    ctx->notifications_3 |= 1 << IAPIPodStateType_ShuffleSetting;
}

void iap_notify_repeat_state(struct IAPContext* ctx, uint8_t state) {
    ctx->notification_data.repeat_state = state;
    ctx->notifications_3 |= 1 << IAPIPodStateType_RepeatSetting;
}

void iap_notify_time_setting(struct IAPContext* ctx, const struct IAPDateTime* time) {
    ctx->notification_data.time_setting = *time;
    ctx->notifications_3 |= 1 << IAPIPodStateType_DateTimeSetting;
}

void iap_notify_hold_switch_state(struct IAPContext* ctx, uint8_t state) {
    ctx->notification_data.hold_switch_state = state;
    ctx->notifications_3 |= 1 << IAPIPodStateType_HoldSwitchState;
}

IAPBool iap_periodic_tick(struct IAPContext* ctx) {
    if(ctx->waiting_for_audio_attrs_ack) {
        return iap_true;
    }

    /* Timer callbacks alone do not establish which track is now playing. */
    iap_platform_refresh_track_state(ctx);

    /* Artwork availability belongs to the new track, even when a new album
     * reuses its queue index. Query from the USB thread, never the playback
     * callback (which may hold playback/playlist locks). */
    if(ctx->track_caps_pending) {
        if(!(ctx->enabled_notifications_3 & (1 << IAPIPodStateType_TrackCaps)) &&
           !(ctx->enabled_notifications_4 & (1 << IAPStatusChangeNotificationType_TrackCapsChanged))) {
            ctx->track_caps_pending = iap_false;
        } else {
            struct IAPPlatformPlayStatus status = {0};
            if(iap_platform_get_play_status(ctx, &status) &&
               status.state != IAPIPodStatePlayStatus_PlaybackStopped &&
               status.track_index == ctx->notification_data.track_playback_index) {
                iap_notify_track_caps(ctx, status.track_caps);
                ctx->track_caps_pending = iap_false;
            }
        }
    }

    ctx->flushing_notifications = iap_true;
    ctx->notification_tick += 1;
    if(!ctx->send_busy) {
        check_ret(_iap_flush_notification(ctx), iap_false);
    }
    return iap_true;
}

static uint8_t play_status_to_extended(uint8_t status) {
    switch(status) {
    case IAPIPodStatePlayStatus_PlaybackStopped:
        return IAPPlayStatusChangeNotificationPlaybackStatusExtendedStates_Stopped;
    case IAPIPodStatePlayStatus_Playing:
        return IAPPlayStatusChangeNotificationPlaybackStatusExtendedStates_Playing;
    case IAPIPodStatePlayStatus_PlaybackPaused:
        return IAPPlayStatusChangeNotificationPlaybackStatusExtendedStates_Paused;
    case IAPIPodStatePlayStatus_FastForward:
        return IAPPlayStatusChangeNotificationPlaybackStatusExtendedStates_FFWSeekStarted;
    case IAPIPodStatePlayStatus_FastRewind:
        return IAPPlayStatusChangeNotificationPlaybackStatusExtendedStates_REWSeekStarted;
    case IAPIPodStatePlayStatus_EndFastForwardRewind:
        return IAPPlayStatusChangeNotificationPlaybackStatusExtendedStates_FFWREWSeekStopped;
    }
    /* unreachable */
    return IAPPlayStatusChangeNotificationPlaybackStatusExtendedStates_Stopped;
}

#define send_notify_3(PayloadType, StateType, set)                                                                                                                      \
    if(ctx->enabled_notifications_3 & ctx->notifications_3 & (1 << StateType)) {                                                                                        \
        struct PayloadType* payload = iap_span_alloc(&request, sizeof(*payload));                                                                                       \
        check_ret(payload != NULL, iap_false);                                                                                                                          \
        payload->type = StateType;                                                                                                                                      \
        set;                                                                                                                                                            \
        check_ret(_iap_send_packet(ctx, IAPLingoID_DisplayRemote, IAPDisplayRemoteCommandID_RemoteEventNotification, _iap_next_trans_id(ctx), request.ptr), iap_false); \
        ctx->notifications_3 &= ~(1 << StateType);                                                                                                                      \
        return iap_true;                                                                                                                                                \
    }

#define send_notify_4(PayloadType, StateType, set)                                                                                                                                   \
    if(ctx->enabled_notifications_4 & ctx->notifications_4 & (1 << StateType)) {                                                                                                     \
        print("notification " #StateType);                                                                                                                                           \
        struct PayloadType* payload = iap_span_alloc(&request, sizeof(*payload));                                                                                                    \
        check_ret(payload != NULL, iap_false);                                                                                                                                       \
        payload->type = StateType;                                                                                                                                                   \
        set;                                                                                                                                                                         \
        check_ret(_iap_send_packet(ctx, IAPLingoID_ExtendedInterface, IAPExtendedInterfaceCommandID_PlayStatusChangeNotification, _iap_next_trans_id(ctx), request.ptr), iap_false); \
        ctx->notifications_4 &= ~(1 << StateType);                                                                                                                                   \
        return iap_true;                                                                                                                                                             \
    }

IAPBool _iap_flush_notification(struct IAPContext* ctx) {
    struct IAPSpan request = _iap_get_buffer_for_send_payload(ctx);

    /* [1] P.257:
     *  Notifications for enabled events are sent every 500 ms,
     *  with the exception of volume change notifications, which are sent every 100 ms.
     */
    if(ctx->notification_tick % 5 != 0) {
        goto freq_events;
    }

    /* Invalidate cached queue-relative identities before sending a possibly
     * unchanged track index from a replacement album/artist. */
    send_notify_3(IAPIPodStatePlaybackEngineContentsPayload,
                  IAPIPodStateType_PlaybackEngineContents,
                  payload->count = swap_32(ctx->notification_data.tracks_count));
    send_notify_4(IAPPlayStatusChangeNotificationPlaybackEngineContentsChangedPayload,
                  IAPStatusChangeNotificationType_PlaybackEngineContentsChanged,
                  payload->count = swap_32(ctx->notification_data.tracks_count));
    /* PCM can reassert elapsed time before each asynchronous HID completion.
     * Send track identity and artwork in both lingoes before that clock. */
    send_notify_4(IAPPlayStatusChangeNotificationTrackUniqueIDPayload,
                  IAPStatusChangeNotificationType_TrackUniqueID,
                  memcpy(payload->id, ctx->notification_data.track_unique_id, sizeof(payload->id)));
    send_notify_3(IAPIPodStateTrackPlaybackIndexPayload,
                  IAPIPodStateType_TrackPlaybackIndex,
                  payload->index = swap_32(ctx->notification_data.track_playback_index));
    send_notify_3(IAPIPodStateTrackCapsPayload,
                  IAPIPodStateType_TrackCaps,
                  payload->caps = swap_32(ctx->notification_data.track_caps));
    send_notify_4(IAPPlayStatusChangeNotificationTrackIndexPayload,
                  IAPStatusChangeNotificationType_TrackIndex,
                  payload->index = swap_32(ctx->notification_data.track_playback_index));
    send_notify_4(IAPPlayStatusChangeNotificationTrackCapsChangedPayload,
                  IAPStatusChangeNotificationType_TrackCapsChanged,
                  payload->caps = swap_32(ctx->notification_data.track_caps));
    send_notify_3(IAPIPodStatePlayStatusPayload,
                  IAPIPodStateType_PlayStatus,
                  payload->status = ctx->notification_data.play_status);
    send_notify_3(IAPIPodStatePowerPayload,
                  IAPIPodStateType_Power,
                  payload->power_state   = ctx->notification_data.power_state;
                  payload->battery_level = ctx->notification_data.battery_level);
    send_notify_3(IAPIPodStateShuffleSettingPayload,
                  IAPIPodStateType_ShuffleSetting,
                  payload->shuffle_state = ctx->notification_data.shuffle_state);
    send_notify_3(IAPIPodStateRepeatSettingPayload,
                  IAPIPodStateType_RepeatSetting,
                  payload->repeat_state = ctx->notification_data.repeat_state);
    send_notify_3(IAPIPodStateDateTimeSettingPayload,
                  IAPIPodStateType_DateTimeSetting,
                  payload->year   = swap_16(ctx->notification_data.time_setting.year);
                  payload->month  = ctx->notification_data.time_setting.month;
                  payload->day    = ctx->notification_data.time_setting.day;
                  payload->hour   = ctx->notification_data.time_setting.hour;
                  payload->minute = ctx->notification_data.time_setting.minute);
    send_notify_4(IAPPlayStatusChangeNotificationPlaybackStoppedPayload,
                  IAPStatusChangeNotificationType_PlaybackStopped, );
    send_notify_4(IAPPlayStatusChangeNotificationPlaybackStatusExtendedPayload,
                  IAPStatusChangeNotificationType_PlaybackStatusExtended,
                  payload->state = play_status_to_extended(ctx->notification_data.play_status));
    /* All finite state changes must drain before recurring PCM clocks. */
    send_notify_3(IAPIPodStateTrackTimePositionMSecPayload,
                  IAPIPodStateType_TrackTimePositionMSec,
                  payload->position_ms = swap_32(ctx->notification_data.track_time_position_ms));
    send_notify_3(IAPIPodStateTrackTimePositionSecPayload,
                  IAPIPodStateType_TrackTimePositionSec,
                  payload->position_s = swap_16(ctx->notification_data.track_time_position_ms / 1000));
    send_notify_4(IAPPlayStatusChangeNotificationTrackTimeOffsetMSecPayload,
                  IAPStatusChangeNotificationType_TrackTimeOffsetMSec,
                  payload->offset_ms = swap_32(ctx->notification_data.track_time_position_ms));
    send_notify_4(IAPPlayStatusChangeNotificationTrackTimeOffsetSecPayload,
                  IAPStatusChangeNotificationType_TrackTimeOffsetSec,
                  payload->offset_s = swap_32(ctx->notification_data.track_time_position_ms / 1000));
freq_events:
    send_notify_3(IAPIPodStateVolumePayload,
                  IAPIPodStateType_Volume,
                  payload->mute_state = ctx->notification_data.mute_state;
                  payload->ui_volume  = ctx->notification_data.volume);

    ctx->flushing_notifications = iap_false;
    return iap_true;
}
