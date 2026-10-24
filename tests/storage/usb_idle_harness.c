/* Hardware mocks for test_usb_idle.py; production functions are inserted below. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>

#define HZ 100
#define BIT(n) (1 << (n))
/* ACTUAL_TIME_MACROS */
#define LIKELY(x) (x)
#define MIN(a,b) ((a)<(b)?(a):(b))
#define IF_MD(...)
#define STORAGE_ATA 1
#define CMD_STANDBY_IMMEDIATE 0xe0
#define logf(...) ((void)0)
typedef uint64_t sector_t;
enum { Q_STORAGE_TICK=1, Q_STORAGE_SLEEPNOW, Q_STORAGE_SLEEP,
       Q_STORAGE_PRE_WAKE, SYS_USB_CONNECTED, SYS_USB_DISCONNECTED };
static long current_tick, ata_last_activity_value, ata_sleep_timeout, ssd_sleep_tick;
static bool ata_powered, ata_ssd_mode, ssd_deep_asleep, ata_usb_storage_active;
static bool ceata, ata_dma, ata_lba48, ata_error_srst, lit, disk_can_sleep;
static unsigned ata_retries;
static int canflush, wake_result, chunk_result, depth, locks, unlocks;
static unsigned flushes, powers_down, powerups, cache_ops, chunks, active_asserts;
static unsigned default_calls, ide_off, commands, ceata_commands;
static uint64_t total_sectors;
static uint32_t log_sector_size;
static uint8_t ceata_taskfile[16];
static uint32_t power_regs[16], pin_regs[16], ATA_CONTROL, ATA_COMMAND;
static uint32_t ATA_PIO_DVR, ATA_PIO_CSD;
static int ata_mutex;
static void (*on_lock)(void);
#define PWRCON(n) power_regs[n]
#define PCON(n) pin_regs[n]
#define STG_EVENT_ASSERT_ACTIVE(x) do { (void)(x); active_asserts++; } while(0)
static void mutex_lock(int *m) {
    assert(m==&ata_mutex);
    if(on_lock) { void (*hook)(void)=on_lock; on_lock=NULL; hook(); }
    depth++; locks++;
}
static void mutex_unlock(int *m) { assert(m==&ata_mutex && depth>0); depth--; unlocks++; }
static void ata_set_active(void);
static int ata_power_up(void) {
    assert(depth>0); powerups++;
    if(!wake_result) { ata_powered=true; ssd_deep_asleep=false; ata_set_active(); }
    return wake_result;
}
static void ata_flush_cache(void) { assert(depth>0); flushes++; }
static void ata_power_down(void) { assert(depth>0); powers_down++; ata_powered=false; ssd_deep_asleep=true; }
static bool ata_disk_can_sleep(void) { return disk_can_sleep; }
static bool is_backlight_on(bool ignore) { (void)ignore; return lit; }
static void ide_power_enable(bool enabled) { assert(depth>0); if(!enabled) ide_off++; }
static void ceata_wait_idle(void) { assert(depth>0); }
static void ceata_write_multiple_register(int start, const void *p, int size) {
    assert(depth>0 && start==0 && p==ceata_taskfile && size==16); ceata_commands++;
}
static void ata_wait_for_rdy(int timeout) { assert(depth>0 && timeout>0); }
static void ata_write_cbr(uint32_t *reg, uint32_t value) { assert(depth>0); *reg=value; commands++; }
static void sleep(int ticks) { assert(depth>0 && ticks>0); current_tick+=ticks; }
static void yield(void) { ATA_CONTROL |= BIT(1); }
static void commit_dcache_range(void *p, int n) { assert(p && n>0 && depth>0); cache_ops++; }
static void commit_discard_dcache_range(void *p, int n) { assert(p && n>0 && depth>0); cache_ops++; }
static int ata_rw_chunk(uint64_t sector, uint32_t count, void *p, bool write) {
    assert(depth>0 && ata_powered && sector<total_sectors && count>0 && p);
    (void)write; chunks++; current_tick++; return chunk_result;
}
static int ata_reset(void) { assert(depth>0); return 0; }
static int storage_event_default_handler(long id, intptr_t data, long last, int storage) {
    assert(id>0 && data==0 && last==ata_last_activity_value && storage==STORAGE_ATA);
    default_calls++; return 73;
}

/* ACTUAL_ERROR_MACROS */
/* ACTUAL_FUNCTIONS */

static unsigned cases;
static void setup(void) {
    assert(depth==0);
    current_tick=10000; ata_last_activity_value=0; ata_sleep_timeout=7*HZ;
    ssd_sleep_tick=0; ata_powered=true; ata_ssd_mode=true; ssd_deep_asleep=false;
    ata_usb_storage_active=ceata=ata_dma=ata_lba48=ata_error_srst=lit=false;
    disk_can_sleep=true; ata_retries=0; canflush=1; wake_result=chunk_result=0;
    depth=locks=unlocks=0; flushes=powers_down=powerups=cache_ops=chunks=0;
    active_asserts=default_calls=ide_off=commands=ceata_commands=0;
    total_sectors=4096; log_sector_size=512; on_lock=NULL;
    memset(power_regs,0,sizeof(power_regs)); memset(pin_regs,0xff,sizeof(pin_regs));
    ATA_CONTROL=ATA_COMMAND=0; cases++;
}
static void event(long id) { assert(ata_event(id,0)==0); assert(depth==0 && locks==unlocks); }
static void no_sleep(void) { assert(flushes==0 && !powers_down && !ide_off && power_regs[0]==0); }
static void refresh_activity(void) { ata_last_activity_value=current_tick; }
static void attach_at_lock(void) { ata_usb_storage_active=true; }
static void postpone_deep_at_lock(void) { ssd_sleep_tick=current_tick; }
static void light_at_lock(void) { lit=true; }
static void finish_transfer_at_lock(void) {
    unsigned char buffer[512];
    assert(ata_read_sectors(0,1,buffer)==0);
}

int main(void) {
    setup(); event(SYS_USB_CONNECTED); event(Q_STORAGE_TICK); event(Q_STORAGE_SLEEPNOW);
    assert(ata_usb_storage_active && active_asserts==2); no_sleep();
    setup(); ata_powered=false; event(SYS_USB_CONNECTED); event(Q_STORAGE_TICK);
    event(Q_STORAGE_SLEEPNOW); no_sleep(); assert(!ssd_deep_asleep);
    setup(); event(SYS_USB_CONNECTED); long previous=ata_last_activity_value;
    event(Q_STORAGE_SLEEP); assert(ata_last_activity_value==previous); no_sleep();
    setup(); on_lock=refresh_activity; event(Q_STORAGE_SLEEPNOW); no_sleep();
    setup(); on_lock=finish_transfer_at_lock; event(Q_STORAGE_SLEEPNOW);
    assert(chunks==1 && ata_last_activity_value==current_tick); no_sleep();
    setup(); on_lock=attach_at_lock; event(Q_STORAGE_SLEEPNOW); no_sleep();
    setup(); event(Q_STORAGE_TICK); assert(!active_asserts);
    event(SYS_USB_CONNECTED); event(Q_STORAGE_SLEEPNOW); no_sleep();
    setup(); event(Q_STORAGE_SLEEPNOW);
    assert(!ata_powered && flushes==1 && power_regs[0]==BIT(5) && ssd_sleep_tick==current_tick);
    setup(); ata_powered=false; event(Q_STORAGE_TICK); assert(ssd_deep_asleep && ide_off==1);
    setup(); ata_powered=false; lit=true; event(Q_STORAGE_TICK); no_sleep();
    setup(); ata_powered=false; on_lock=attach_at_lock; event(Q_STORAGE_TICK); no_sleep();
    setup(); ata_powered=false; on_lock=postpone_deep_at_lock; event(Q_STORAGE_TICK); no_sleep();
    setup(); ata_powered=false; on_lock=light_at_lock; event(Q_STORAGE_TICK); no_sleep();
    setup(); event(SYS_USB_CONNECTED); event(SYS_USB_DISCONNECTED);
    assert(!ata_usb_storage_active && ata_last_activity_value==current_tick);
    event(Q_STORAGE_SLEEPNOW); no_sleep(); current_tick+=7*HZ; event(Q_STORAGE_SLEEPNOW);
    assert(flushes==1 && !ata_powered);
    setup(); ata_powered=false; event(SYS_USB_CONNECTED); event(SYS_USB_DISCONNECTED);
    event(Q_STORAGE_TICK); no_sleep(); current_tick+=30*HZ; event(Q_STORAGE_TICK); no_sleep();
    current_tick++; event(Q_STORAGE_TICK); assert(ssd_deep_asleep && ide_off==1);
    setup(); event(Q_STORAGE_SLEEP); event(Q_STORAGE_SLEEPNOW); no_sleep();
    current_tick+=HZ/5; event(Q_STORAGE_SLEEPNOW); assert(flushes==1);
    setup(); ata_ssd_mode=false; event(Q_STORAGE_SLEEPNOW);
    assert(powers_down==1 && commands==2 && ATA_PIO_CSD==CMD_STANDBY_IMMEDIATE);
    setup(); ceata=true; event(Q_STORAGE_SLEEPNOW); assert(powers_down==1 && ceata_commands==1);
    setup(); ata_ssd_mode=false; disk_can_sleep=false; event(Q_STORAGE_SLEEPNOW); assert(powers_down==1);
    setup(); ata_sleepnow(); assert(depth==0 && locks==unlocks && flushes==1 && !ata_powered);
    setup(); event(SYS_USB_CONNECTED); ata_sleepnow();
    assert(depth==0 && locks==unlocks && flushes==1); /* explicit shutdown API stays explicit */
    setup(); ata_powered=false; event(Q_STORAGE_PRE_WAKE); assert(ata_powered && powerups==1);
    setup(); ata_powered=false; wake_result=ERR_RC(7); event(Q_STORAGE_PRE_WAKE);
    assert(!ata_powered && powerups==1 && depth==0);
    unsigned char buffer[513*512];
    setup(); ata_powered=false; ata_dma=true; wake_result=ERR_RC(7);
    assert(IS_ERR(ata_read_sectors(0,1,buffer))); assert(powerups==1 && !cache_ops && !chunks && !ATA_COMMAND);
    assert(depth==0 && locks==unlocks);
    setup(); ata_powered=false; ata_dma=true; wake_result=ERR_RC(7);
    assert(IS_ERR(ata_write_sectors(0,1,buffer))); assert(powerups==1 && !cache_ops && !chunks && !ATA_COMMAND);
    assert(depth==0 && locks==unlocks);
    setup(); ata_dma=true; assert(ata_read_sectors(0,513,buffer)==0);
    assert(chunks==3 && cache_ops==1 && ata_last_activity_value==current_tick && depth==0);
    setup(); ata_powered=false; assert(ata_read_sectors(0,1,buffer)==0);
    assert(powerups==1 && chunks==1 && depth==0);
    setup(); assert(IS_ERR(ata_read_sectors(4096,1,buffer))); assert(!cache_ops && !chunks && depth==0);
    setup(); chunk_result=ERR_RC(9); assert(IS_ERR(ata_read_sectors(0,1,buffer)));
    assert(chunks==1 && depth==0 && locks==unlocks);
    setup(); assert(ata_event(99,0)==73 && default_calls==1 && depth==0);
    setup(); current_tick=LONG_MAX-300; ata_last_activity_value=current_tick;
    event(Q_STORAGE_SLEEPNOW); no_sleep();
    current_tick=(long)((unsigned long)current_tick+7UL*HZ);
    event(Q_STORAGE_SLEEPNOW); assert(flushes==1 && !ata_powered);
    setup(); ata_powered=false; current_tick=ssd_sleep_tick=LONG_MAX-1500;
    event(Q_STORAGE_TICK); no_sleep();
    current_tick=(long)((unsigned long)current_tick+30UL*HZ+1);
    event(Q_STORAGE_TICK); assert(ssd_deep_asleep && ide_off==1);
    setup(); current_tick=LONG_MAX-300; event(SYS_USB_CONNECTED); event(SYS_USB_DISCONNECTED);
    current_tick=(long)((unsigned long)current_tick+7UL*HZ-1);
    event(Q_STORAGE_SLEEPNOW); no_sleep(); current_tick++;
    event(Q_STORAGE_SLEEPNOW); assert(flushes==1 && !ata_powered);
    printf("PASS: %u actual ATA policy/transfer cases; ASan/UBSan (legacy error-macro shift-base excluded)\n",cases);
    return 0;
}
