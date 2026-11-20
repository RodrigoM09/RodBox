"""Production PCM/mixer + PCMBUF + CS42L55 lifecycle reproduction.

The reliability-first policy keeps the codec under normal audio init/close,
not a single music channel. Shared idle savings remain deferred. Default mode
requires the corrected policy; --expect-pb55-defect characterizes the old source.
Synthetic hardware/scheduling only; no device I/O or physical acceptance.
"""
import sys
from pb56_analog_harness import COMMON, function, no_includes, run_c, text

code = COMMON + r'''
#define HAVE_CS42L55
#define USB_ENABLE_IAP
#define HAVE_USB_HOST_AUDIO
#define CONFIG_CPU 8702
#define PP5002 5002
#define JZ4760B 4760
#define JZ4732 4732
#define CONFIG_PLATFORM 1
#define PLATFORM_HOSTED 8
#define ASSUME(x) assert(x)
#define SAMPR_96 96000
#define SAMPR_48 48000
#define SYS_EVENT_OUTPUT_GONE 1
#define SYS_EVENT_OUTPUT_BACK 2
#define OUTPUT_DAC 1
#define OUTPUT_ACCESSORY 2
#define AUDIOHW_SETTING(...)
#define HW_FREQ_8 0
#define HW_FREQ_11 1
#define HW_FREQ_12 2
#define HW_FREQ_16 3
#define HW_FREQ_22 4
#define HW_FREQ_24 5
#define HW_FREQ_32 6
#define HW_FREQ_44 7
#define HW_FREQ_48 8
static long current_tick;
static bool in_irq;
static int stop_in_irq, codec_io_in_irq, wake_count, down_count;
static unsigned char registers[256];
static unsigned char cscodec_read(int reg) { codec_io_in_irq += in_irq; return registers[reg]; }
static void cscodec_write(int reg, unsigned char value) { codec_io_in_irq += in_irq; registers[reg] = value; }
static void cscodec_power(bool b) {}
static void cscodec_clock(bool b) {}
static void cscodec_reset(bool b) {}
static void sleep(int ticks) {}
static void udelay(int us) { assert(!in_irq); }
static void send_event(int e, void *p) {}
static int round_value_to_list32(unsigned long value, const unsigned long *list, int n, bool b) {
    for (int i=0;i<n;i++) if(list[i]==value)return i;
    return 0;
}
static void **find_array_ptr(void **a, void *p) { while(*a && *a!=p)a++; return a; }
static void remove_array_ptr(void **a, void *p) {
    a=find_array_ptr(a,p); if(*a) do { *a=*(a+1); a++; } while(*a);
}
static int16_t clip_sample_16(int32_t x) { return MAX(-32768, MIN(32767,x)); }
'''
for header in ['pcm_sink.h', 'pcm.h', 'pcm-internal.h', 'pcm_mixer.h', 'cs42l55.h']:
    code += no_includes(text('firmware/export/' + header))
code += r'''
static bool i2s_running;
static const unsigned long rates[] = {44100};
static void fake_init(void) {}
static void fake_freq(uint16_t f) {}
static void fake_lock(void) {}
static void fake_unlock(void) {}
static void builtin_play(const void *a, size_t s) { assert(a && s); i2s_running=true; }
static void builtin_stop(void) { stop_in_irq += in_irq; i2s_running=false; }
static void digital_play(const void *a, size_t s) { assert(a && s); }
static void digital_stop(void) {}
#define FAKE_SINK(play,stop) { .caps={rates,1,0,PCM_SINK_HWVOL}, .ops={fake_init,fake_init,fake_freq,fake_lock,fake_unlock,play,stop} }
struct pcm_sink builtin_pcm_sink = FAKE_SINK(builtin_play,builtin_stop);
struct pcm_sink iap_pcm_sink = FAKE_SINK(digital_play,digital_stop);
struct pcm_sink usb_host_pcm_sink = FAKE_SINK(digital_play,digital_stop);
'''
code += no_includes(text('firmware/pcm.c'))
code += no_includes(text('firmware/asm/pcm-mixer.c'))
code += no_includes(text('firmware/pcm_mixer.c'))
codec = text('firmware/drivers/audio/cs42l55.c')
for name in ['audiohw_mute', 'cscodec_setbits']:
    pass
code += function(codec, 'cscodec_setbits') + function(codec, 'audiohw_mute')
code += function(codec, 'audiohw_idle_powerdown').replace('audiohw_mute(true);', 'down_count++; audiohw_mute(true);')
code += function(codec, 'audiohw_idle_powerup').replace('/* Clear PDN_CODEC', 'wake_count++;\n    /* Clear PDN_CODEC')
code += r'''
static uint32_t samples[MIX_FRAME_SAMPLES * 8];
static int chunk_widx=1, chunk_ridx;
static void *current_desc;
static bool pcmbuf_sync_position;
static void pcmbuf_pcm_callback(const void **p, size_t *s) { *p=samples; *s=sizeof(samples); }
static void pcmbuf_sampr_callback(uint32_t rate) {}
static void init_buffer_state(void) { chunk_widx=1;chunk_ridx=0; }
static void crossfade_cancel(void) {}
static void boost_codec_thread(int x) {}
'''
pcmbuf = text('apps-ipod/audio/pcmbuf.c')
code += function(pcmbuf, 'pcmbuf_play_start') + function(pcmbuf, 'pcmbuf_play_stop')
code += r'''
static bool codec_awake(void) { return !(registers[PWRCTL1] & PWRCTL1_PDN_CODEC) && !(registers[PLAYCTL] & (PLAYCTL_MSTAMUTE|PLAYCTL_MSTBMUTE)); }
static void reset(void) {
    mixer_reset(); memset(channels,0,sizeof(channels));
    pcm_switch_sink(PCM_SINK_BUILTIN);
    memset(registers,0,sizeof(registers));
    registers[HPACTL]=0x65;registers[HPBCTL]=0x71;
    registers[LINEACTL]=0x02;registers[LINEBCTL]=0x03;
    wake_count=down_count=stop_in_irq=codec_io_in_irq=0;
    init_buffer_state();
    for(int i=0;i<PCM_MIXER_NUM_CHANNELS;i++)mixer_channel_set_amplitude(i,MIX_AMP_UNITY);
}
static void consumer(enum pcm_mixer_channel chan) {
    mixer_channel_play_data(chan,NULL,samples,sizeof(samples));
    assert(mixer_channel_status(chan)==CHANNEL_PLAYING);
}
int main(int argc,char **argv) {
    bool require_fixed = !(argc>1 && !strcmp(argv[1],"--expect-pb55-defect"));
    pcm_init(); pcm_postinit();
    for(unsigned i=0;i<ARRAYLEN(samples);i++)samples[i]=0xffd2007b; /* L=123,R=-46 */
    reset();pcmbuf_play_start();
    assert(i2s_running && codec_awake());
    /* A second consumer has no wake path and must survive music stop. */
    consumer(PCM_MIXER_CHAN_VOICE);pcmbuf_play_stop();
    assert(mixer_channel_status(PCM_MIXER_CHAN_VOICE)==CHANNEL_PLAYING);
    assert(i2s_running);
    printf("overlap: voice=playing PCM=%d codec_awake=%d (expected 1)\n",pcm_is_playing(),codec_awake());fflush(stdout);
    if(require_fixed)assert(codec_awake() && "music stop must not power down active voice");
    else assert(!codec_awake());
    /* Later voice/beep must also be able to wake from a music stop. */
    for(int ch=PCM_MIXER_CHAN_VOICE;ch<=PCM_MIXER_CHAN_BEEP;ch++) {
        reset();pcmbuf_play_start();pcmbuf_play_stop();consumer(ch);
        printf("stop->%s: PCM=%d codec_awake=%d (expected 1)\n",ch==PCM_MIXER_CHAN_VOICE?"voice":"beep",pcm_is_playing(),codec_awake());
        assert(!require_fixed ? !codec_awake() : codec_awake());
        assert(registers[HPACTL]==0x65 && registers[HPBCTL]==0x71);
        assert(registers[LINEACTL]==0x02 && registers[LINEBCTL]==0x03);
    }
    /* Prove analog is touched unnecessarily for both digital output routes. */
    for(int sink=PCM_SINK_IAP;sink<=PCM_SINK_USB_HOST;sink++) {
        reset();assert(pcm_switch_sink(sink));pcmbuf_play_start();pcmbuf_play_stop();
        printf("digital sink %d: codec wakes=%d powerdowns=%d (expected 0,0)\n",sink,wake_count,down_count);
        assert(!require_fixed ? wake_count==1 && down_count==1 : !wake_count && !down_count);
    }
    /* Shared mixer naturally stops in DMA completion/IRQ after 3s silence.
       Relocating codec I2C calls into this stop op would be unsafe. */
    reset();consumer(PCM_MIXER_CHAN_VOICE);mixer_channel_stop(PCM_MIXER_CHAN_VOICE);
    int frames=0;const void *p;size_t n;
    in_irq=true;
    while(pcm_is_playing() && frames++<1000) {
        pcm_play_dma_status_callback(PCM_DMAST_STARTED);
        pcm_play_dma_complete_callback(PCM_DMAST_OK,&p,&n);
    }
    in_irq=false;
    assert(!pcm_is_playing() && stop_in_irq && !codec_io_in_irq);
    printf("shared idle stop: frames=%d stop_in_irq=%d codec_IO_in_irq=%d\n",frames,stop_in_irq,codec_io_in_irq);
    /* Verify portable production mixer preserves stereo pair order. */
    reset();consumer(PCM_MIXER_CHAN_VOICE);
    assert(downmix_buf[downmix_index][0]==0xffd2007b);
    puts(require_fixed ? "PASS: music stop preserves shared voice/beep output; digital sinks avoid analog power calls; no codec I/O in IRQ; stored gains/stereo retained" : "PASS: known PB55 lifecycle defects characterized; not a fix");
}
'''
result = run_c(code, sys.argv[1:])
print(result.stdout, end='')
print(result.stderr, end='', file=sys.stderr)
if result.returncode:
    raise SystemExit(1)
