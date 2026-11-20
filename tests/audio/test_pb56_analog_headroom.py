"""Production sound.c gain-policy regression, ASan/UBSan; hardware setters observed.

No DSP or analog response is simulated: asserts commanded attenuation/gains.
The neutral and legacy target paths must retain their previous exact behavior.
"""
import sys
from pb56_analog_harness import COMMON, function, run_c, text

sound = text('firmware/sound.c')
# Keep production scaler state declaration and the entire policy, not a model.
start = sound.index('static struct\n{\n    int volume;')
end = sound.index('void sound_set_volume(int value)')
code = COMMON + r'''
#define AUDIOHW_HAVE_BASS
#define AUDIOHW_HAVE_TREBLE
#define AUDIOHW_HAVE_LINEOUT
#define SOUND_VOLUME 0
#define SOUND_BASS 1
#define SOUND_TREBLE 2
static bool audio_is_initialized=true;
static struct {int volume_limit;} global_settings={12};
static struct {int volume;} global_status;
static int attenuation, left, right, line_left, line_right, bass_setting, treble_setting;
static int sound_numdecimals(int s) { return s==SOUND_VOLUME?0:1; }
static int sound_min(int s) { return -60; }
static int sound_max(int s) { return 12; }
static void audiohw_set_prescaler(int v) { attenuation=v; }
#ifdef AUDIOHW_HAVE_MONO_VOLUME
static void audiohw_set_volume(int v) { left=right=v; }
#else
static void audiohw_set_volume(int l,int r) { left=l;right=r; }
#endif
static void audiohw_set_lineout_volume(int l,int r) { line_left=l;line_right=r; }
static void audiohw_set_bass(int v) { bass_setting=v; }
static void audiohw_set_treble(int v) { treble_setting=v; }
'''
code += function(sound, 'sound_value_to_cb')
code += sound[start:end]
for name in ['sound_set_volume', 'sound_set_balance', 'sound_set_bass', 'sound_set_treble']:
    code += function(sound, name)
code += r'''
int main(int argc,char **argv) {
    bool strict=argc>1 && !strcmp(argv[1],"--boost");
    sound_set_volume(12);sound_set_bass(120);
    printf("native boost +12 dB at volume +12 dB: attenuation=%d cb analog L/R=%d/%d cb\n",attenuation,left,right);fflush(stdout);
    if(strict)assert(attenuation==120 && "retain all tone headroom at maximum volume");
    else assert(attenuation==0); /* Legacy/mono/simulator exact behavior */
    unsigned cases=0;
    for(int v=-60;v<=12;v++) {
        sound_set_balance(0);sound_set_bass(0);sound_set_treble(0);sound_set_volume(v);
        assert(attenuation==0 && left==v*10 && right==v*10);
        assert(line_left==0 && line_right==0);
        if(!strict)continue;
        for(int bass=-105;bass<=120;bass+=15)for(int treble=-105;treble<=120;treble+=15) {
            sound_set_bass(bass);sound_set_treble(treble);
            int boost=MAX(0,MAX(bass,treble));
            int compensated=v<=-60?v*10:MIN(120,v*10+boost);
            assert(attenuation==boost && left==compensated && right==compensated);
            assert(bass_setting==bass && treble_setting==treble);
            assert(line_left==0 && line_right==0);
            /* Exact command-domain headroom for a full-scale band peak:
               prescale + boost <= 0 dB before compensating analog volume. */
            assert(boost-attenuation<=0);
            sound_set_balance(100);assert(left==-600 && right==compensated);
            sound_set_balance(-100);assert(right==-600 && left==compensated);
            sound_set_balance(0);
            cases++;
        }
    }
    sound_set_bass(0);sound_set_treble(0);
    sound_set_volume(99);assert(left==120 && global_status.volume==12);
    sound_set_volume(-99);assert(left==-600 && global_status.volume==-60);
    global_settings.volume_limit=-20;sound_set_volume(12);assert(left==-200 && global_status.volume==-20);
    puts(strict?"PASS: full tone headroom retained; neutral gain, mute, balance, unity lineout, limits unchanged":"PASS: legacy/mono/simulator policy and neutral gains unchanged");
    printf("boost/volume cases=%u\n",cases);
}
'''
configs = [('native-cs42l55', ['HAVE_CS42L55'], ['--boost'])]
if '--matrix' in sys.argv:
    configs += [('legacy-other-codec', [], []),
                ('cs42l55-simulator', ['HAVE_CS42L55', 'SIMULATOR'], []),
                ('mono-other-codec', ['AUDIOHW_HAVE_MONO_VOLUME'], []),
                ('cs42l55-mono-guard', ['HAVE_CS42L55','AUDIOHW_HAVE_MONO_VOLUME'], [])]
for name, defines, args in configs:
    print('CONFIG:', name, flush=True)
    result=run_c(code,args,defines)
    print(result.stdout,end='')
    print(result.stderr,end='',file=sys.stderr)
    if result.returncode:
        raise SystemExit(1)
