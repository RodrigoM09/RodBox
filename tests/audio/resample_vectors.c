/* Host fixture: includes the real production resampler, not a DSP model.
 * Only firmware platform/configuration services are stubbed by the runner. */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "resample.c"

struct dsp_config { unsigned id, fout; bool active; };
unsigned dsp_get_id(const struct dsp_config *d) { return d->id; }
unsigned dsp_get_output_frequency(struct dsp_config *d) { return d->fout; }
void dsp_proc_enable(struct dsp_config *d, enum dsp_proc_ids id, bool on)
{ (void)d; (void)id; (void)on; }
void dsp_proc_activate(struct dsp_config *d, enum dsp_proc_ids id, bool on)
{ (void)id; d->active = on; }
bool dsp_proc_active(struct dsp_config *d, enum dsp_proc_ids id)
{ (void)id; return d->active; }
void dsp_proc_set_in_place(struct dsp_config *d, enum dsp_proc_ids id, bool on)
{ (void)d; (void)id; (void)on; }
void dsp_proc_want_format_update(struct dsp_config *d, enum dsp_proc_ids id)
{ (void)d; (void)id; }

#define N 32768
#define AMP (1 << 25)
static int32_t input[2][N], output[2][N * 6], reference[2][N * 6];

/* Feed realistic upstream chunks and drain the production stage's 192-frame
 * output, including its source-consumption and format-change entry points. */
static int run(unsigned fin, unsigned fout, unsigned channels, int chunk,
               int32_t out[2][N * 6])
{
    memset(resample_data, 0, sizeof resample_data);
    struct dsp_config dsp = {0, fout, false};
    struct dsp_proc_entry entry = {0};
    dsp_resample_init(&dsp, 0);
    resample_configure(&entry, &dsp, DSP_PROC_INIT, 0);
    struct sample_format format = {.num_channels=channels, .frequency=fin,
                                  .codec_frequency=fin, .frac_bits=27};
    resample_configure(&entry, &dsp, DSP_PROC_NEW_FORMAT, (intptr_t)&format);
    int total = 0;
    for (int offset = 0; offset < N;) {
        int count = MIN(chunk, N - offset);
        struct dsp_buffer source = {.remcount=count,
            .p32={input[0]+offset, input[channels == 1 ? 0 : 1]+offset},
            .format=format};
        while (source.remcount) {
            struct dsp_buffer *buf = &source;
            if (dsp.active) entry.process(&entry, &buf);
            assert(buf->remcount > 0 || source.remcount == 0);
            assert(total + buf->remcount <= N * 6);
            for (unsigned ch=0; ch<channels; ++ch)
                memcpy(out[ch]+total, buf->p32[ch], buf->remcount*sizeof(int32_t));
            total += buf->remcount;
            buf->remcount = 0; /* model downstream draining */
        }
        offset += count;
    }
    return total;
}

static double tone(unsigned fin, unsigned fout, double hz, int chunk)
{
    for (int i=0; i<N; ++i) {
        input[0][i] = (int32_t)llround(AMP * sin(2*M_PI*hz*i/fin));
        input[1][i] = -input[0][i];
    }
    int count = run(fin, fout, 2, chunk, output);
    double energy=0;
    for (int i=2048; i<count; ++i) {
        double x = output[0][i];
        energy += x*x;
        assert(llabs((long long)output[0][i]+output[1][i]) <= 8);
    }
    return 20*log10(sqrt(2*energy/(count-2048))/AMP + 1e-15);
}

int main(int argc, char **argv)
{
    if (argc == 2 && !strcmp(argv[1], "selftest")) {
        const unsigned rates[][2] = {{44100,44100},{48000,48000},
            {22050,44100},{32000,48000},{96000,48000},{88200,44100},{48000,44100}};
        uint32_t seed = 123;
        for (int i=0;i<N;i++) {
            seed = seed*1664525u+1013904223u;
            input[0][i]=(int32_t)(seed&0xffffff)-0x800000;
            input[1][i]=-input[0][i];
        }
        for (unsigned k=0;k<sizeof rates/sizeof rates[0];k++) {
            for (unsigned ch=1;ch<=2;ch++) {
                int a=run(rates[k][0],rates[k][1],ch,509,reference);
                int b=run(rates[k][0],rates[k][1],ch,97,output);
                assert(a==b && a>0);
                for (unsigned c=0;c<ch;c++)
                    assert(!memcmp(reference[c],output[c],a*sizeof(int32_t)));
                if (rates[k][0]==rates[k][1]) {
                    assert(a==N);
                    for (unsigned c=0;c<ch;c++)
                        assert(!memcmp(input[c],output[c],N*sizeof(int32_t)));
                }
            }
        }
        puts("PASS: native-rate sample identity and mono/stereo chunk continuity for seven rate pairs (portable production C)");
        return 0;
    }
    if (argc == 6 && !strcmp(argv[1], "tone")) {
        unsigned fin = strtoul(argv[2],0,10), fout=strtoul(argv[3],0,10);
        printf("%.9f\n", tone(fin, fout, strtod(argv[4],0), atoi(argv[5])));
        return 0;
    }
    fprintf(stderr, "usage: %s tone input-rate output-rate tone-Hz chunk\n", argv[0]);
    return 2;
}
