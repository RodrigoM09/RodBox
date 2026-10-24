"""Run the actual four driver function bodies with mocked hardware primitives.

This exercises return propagation and waiting behavior; it does not emulate
DesignWare hardware, bus enumeration, IRQ timing, or accessory streaming.
"""
from pathlib import Path
import re, subprocess, tempfile, sys

base = Path(__file__).resolve().parent
driver = Path(sys.argv[1]) if len(sys.argv)>1 else base.parents[1]/'firmware-source/firmware/drivers/usb-designware.c'
source = driver.read_text()
names = ['usb_dw_transfer', 'usb_drv_recv_nonblocking', 'usb_drv_send_nonblocking', 'usb_drv_send']
def extract(name):
    match = re.search(r'^(?:static )?int ' + name + r'\(', source, re.M)
    assert match, name
    start = source.index('{', match.start())
    depth = 1
    end = start + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[match.start():end]

header = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#define HZ 100
#define OBJ_WAIT_TIMEDOUT -1
#define EP_NUM(endpoint) ((endpoint) & 15)
#define logf(...) ((void)0)
enum usb_dw_epdir { USB_DW_EPDIR_IN, USB_DW_EPDIR_OUT };
struct usb_dw_ep { bool active, busy; void *req_addr; uint32_t req_size; int complete, status; };
static struct usb_dw_ep endpoints[4][2];
static uint32_t mps[4][2];
static int irq_depth, starts, waits, aborts;
static bool timeout;
static struct usb_dw_ep *usb_dw_get_ep(int n, enum usb_dw_epdir d) { return &endpoints[n][d]; }
static uint32_t usb_dw_maxpktsize(int n, enum usb_dw_epdir d) { return mps[n][d]; }
static void usb_dw_epstart(int n, enum usb_dw_epdir d, void *p, uint32_t size) {
    (void)n; (void)d; (void)p; (void)size; assert(irq_depth == 1); starts++;
}
static void usb_dw_target_disable_irq(void) { assert(irq_depth == 0); irq_depth++; }
static void usb_dw_target_enable_irq(void) { assert(irq_depth == 1); irq_depth--; }
static int semaphore_wait(int *s, int ticks) { (void)s; if (ticks) waits++; return ticks && timeout ? OBJ_WAIT_TIMEDOUT : 0; }
static void usb_dw_abort_endpoint(int n, enum usb_dw_epdir d) { assert(irq_depth == 1); aborts++; endpoints[n][d].status = -99; }
'''
tests = r'''
static void reset(void) {
    memset(endpoints, 0, sizeof(endpoints)); memset(mps, 0, sizeof(mps));
    irq_depth = starts = waits = aborts = 0; timeout = false;
}
int main(void) {
    char data[512];
    for (int d = 0; d < 2; d++) {
        reset();
        endpoints[1][d].req_addr = data + 1; endpoints[1][d].req_size = 7;
        mps[1][d] = 512;
        int rc = d == USB_DW_EPDIR_IN ? usb_drv_send_nonblocking(0x81,data,512) : usb_drv_recv_nonblocking(1,data,512);
        assert(rc == -1 && starts == 0 && irq_depth == 0);
        assert(endpoints[1][d].req_addr == data + 1 && endpoints[1][d].req_size == 7);
        puts(d ? "PASS inactive OUT: reject, preserve request, restore IRQ" : "PASS inactive IN: reject, preserve request, restore IRQ");
        reset(); endpoints[1][d].active = true;
        rc = d == USB_DW_EPDIR_IN ? usb_drv_send_nonblocking(0x81,data,512) : usb_drv_recv_nonblocking(1,data,512);
        assert(rc == -1 && starts == 0 && irq_depth == 0);
        puts(d ? "PASS active OUT with zero packet size: reject" : "PASS active IN with zero packet size: reject");
        reset(); endpoints[1][d].active = true; mps[1][d] = 512;
        rc = d == USB_DW_EPDIR_IN ? usb_drv_send_nonblocking(0x81,data,512) : usb_drv_recv_nonblocking(1,data,512);
        assert(rc == 0 && starts == 1 && irq_depth == 0);
        assert(endpoints[1][d].req_addr == data && endpoints[1][d].req_size == 512);
        puts(d ? "PASS valid OUT: starts request" : "PASS valid IN: starts request");
    }
    reset(); endpoints[0][USB_DW_EPDIR_IN].active = true;
    assert(usb_drv_send_nonblocking(0x80,NULL,0) == 0 && starts == 1 && irq_depth == 0);
    puts("PASS EP0 zero-length status transfer remains allowed");
    reset(); mps[1][USB_DW_EPDIR_IN] = 512;
    assert(usb_drv_send(0x81,data,512) == -1 && waits == 0 && starts == 0 && irq_depth == 0);
    puts("PASS blocking inactive IN: returns without waiting for impossible completion");
    reset(); endpoints[1][USB_DW_EPDIR_IN].active = true;
    assert(usb_drv_send(0x81,data,512) == -1 && waits == 0 && starts == 0 && irq_depth == 0);
    puts("PASS blocking zero packet size: returns without completion wait");
    reset(); endpoints[1][USB_DW_EPDIR_IN].active = true; mps[1][USB_DW_EPDIR_IN] = 512;
    assert(usb_drv_send(0x81,data,512) == 0 && starts == 1 && waits == 1 && aborts == 0 && irq_depth == 0);
    puts("PASS normal blocking IN: completion path retained");
    reset(); endpoints[1][USB_DW_EPDIR_IN].active = true; mps[1][USB_DW_EPDIR_IN] = 512; timeout = true;
    assert(usb_drv_send(0x81,data,512) == -99 && starts == 1 && waits == 1 && aborts == 1 && irq_depth == 0);
    puts("PASS timeout: existing abort and status propagation retained");
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='rodbox-usb-test-') as directory:
    p = Path(directory)
    (p / 'test.c').write_text(header + '\n\n'.join(map(extract,names)) + tests)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
    result = subprocess.run([str(p/'test')],check=True,capture_output=True,text=True)
    print(result.stdout,end='')
    # Results are printed; callers may capture them outside the source tree.
