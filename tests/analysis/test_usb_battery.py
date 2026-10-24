"""Exercise the actual USB indicator renderer against a stale framebuffer."""
from pathlib import Path
import subprocess,tempfile

root=Path(__file__).resolve().parents[2]
source=(root/'firmware-source/apps-ipod/screens/system/usb_screen.c').read_text()
start=source.index('static void usb_battery_draw(bool force)\n{')
body=source[start:source.index('\nvoid gui_usb_screen_run',start)]
run=source[source.index('void gui_usb_screen_run'):]
assert run.index('usb_acknowledge(')<run.index('usb_battery_draw(true)')
pre=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#define NB_SCREENS 1
#define FOR_NB_SCREENS(i) for(int i=0;i<NB_SCREENS;i++)
#define FONT_SYSFIXED 0
#define SYSFONT_HEIGHT 8
#define DRMODE_FG 1
#define DRMODE_SOLID 3
#define LCD_BLACK 0
#define LCD_WHITE 255
#define MIN(a,b) ((a)<(b)?(a):(b))
enum {BATTERY_DISPLAY_ICON,BATTERY_DISPLAY_PERCENT,BATTERY_DISPLAY_BOTH};
struct viewport {int font,x,y,width,height;};
static unsigned char pixels[240][320];
static struct viewport *current;
static int level=50,foreground=255,updates,texts,rectangles,drawmode;
static bool charging;
static struct {int battery_display;} global_settings;
static int battery_level(void){return level;}
static bool charging_state(void){return charging;}
static void fill(int x,int y,int w,int h){
 assert(current && x>=0 && y>=0 && x+w<=current->width && y+h<=current->height);
 for(int yy=y;yy<y+h;yy++)for(int xx=x;xx<x+w;xx++)pixels[current->y+yy][current->x+xx]=foreground;
}
static void clear(void){int old=foreground;foreground=17;fill(0,0,current->width,current->height);foreground=old;}
static struct viewport *setvp(struct viewport *p){struct viewport *old=current;current=p;return old;}
static void rect(int x,int y,int w,int h){rectangles++;fill(x,y,w,1);fill(x,y+h-1,w,1);fill(x,y,1,h);fill(x+w-1,y,1,h);}
static void text(int x,int y,const char *s){texts++;fill(x,y,(int)strlen(s)*6,8);}
static void update(void){updates++;}
static void color(unsigned c){foreground=(int)c;}
static void mode(int m){drawmode=m;}
struct screen {int screen_type,lcdwidth,lcdheight;
 struct viewport *(*set_viewport)(struct viewport *);
 void (*clear_viewport)(void);void (*putsxy)(int,int,const char *);
 void (*update_viewport)(void);void (*drawrect)(int,int,int,int);
 void (*fillrect)(int,int,int,int);void (*set_foreground)(unsigned);
 void (*set_drawmode)(int);};
static struct screen screens[]={{0,320,240,setvp,clear,text,update,rect,fill,color,mode}};
static void viewport_set_defaults(struct viewport *p,int t){(void)t;*p=(struct viewport){0,0,0,320,240};}
static void font_getstringsize(const char *s,int *w,void *h,int f){(void)h;(void)f;*w=(int)strlen(s)*6;}
'''
tests=r'''
int main(void){
 int cases=0;
 for(int presentation=0;presentation<3;presentation++)
 for(int state=0;state<2;state++)
 for(int value=-1;value<=100;value+=(value==-1?1:50)){
  memset(pixels,17,sizeof(pixels));global_settings.battery_display=presentation;
  charging=state;level=value;updates=texts=rectangles=0;current=NULL;
  usb_battery_draw(true);
  assert(updates==2 && current==NULL && drawmode==DRMODE_SOLID);
  assert(rectangles==(presentation==BATTERY_DISPLAY_PERCENT?0:1));
  assert(texts==(presentation==BATTERY_DISPLAY_ICON?1:2));
  for(int y=0;y<35;y++)for(int x=0;x<320;x++)assert(pixels[y][x]!=17);
  /* Erase the entire old clock/icon region, including below y=20. */
  assert(pixels[28][290]==0 && pixels[15][200]==0);
  for(int y=35;y<224;y++)for(int x=0;x<320;x++)assert(pixels[y][x]==17);
  usb_battery_draw(false);assert(updates==2);
  charging=!charging;usb_battery_draw(false);assert(updates==4);
  cases++;
 }
 printf("PASS: %d mode/power/level framebuffer cases; cached repaint, viewport restoration and post-ACK order; ASan/UBSan\n",cases);
}
'''
with tempfile.TemporaryDirectory(prefix='rodbox-usb-battery-') as tmp:
    p=Path(tmp);(p/'test.c').write_text(pre+body+tests)
    subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-O1','-g',
                    '-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
