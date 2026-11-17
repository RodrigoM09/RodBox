"""Production Classic percentage helper and actual voltage tables; no device I/O."""
from pathlib import Path
import re,subprocess,tempfile
r=Path(__file__).resolve().parents[2]
s=(r/'firmware-source/firmware/powermgmt.c').read_text()
a=s.index('static int classic_battery_percent(');b=s.index('\n#endif',a)
h=s[a:b]
t=(r/'firmware-source/firmware/target/arm/s5l8702/ipod6g/powermgmt-6g.c').read_text()
tables={name:list(map(int,re.search(name+r'\[11\]\s*=\s*\{([^}]+)',t).group(1).replace(',',' ').split())) for name in ['percent_to_volt_charge','percent_to_volt_discharge']}
def pct(v,t):
 for i in range(10):
  if v<=t[i+1]:return i*10+(v-t[i])*10//(t[i+1]-t[i])
 return 100
assert pct(3998,tables['percent_to_volt_charge'])==42
assert pct(3998,tables['percent_to_volt_discharge'])==82
code='''#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
'''+h+'''
int main(void){
 assert(classic_battery_percent(-1,false)==-1);
 assert(classic_battery_percent(42,true)==42);
 for(int i=0;i<100;i++)assert(classic_battery_percent(82,false)==42);
 assert(classic_battery_percent(41,false)==41);
 assert(classic_battery_percent(20,true)==41);
 assert(classic_battery_percent(45,true)==45);
 assert(classic_battery_percent(99,true)==99);
 assert(classic_battery_percent(100,true)==100);
 assert(classic_battery_percent(95,false)==95);
 assert(classic_battery_percent(0,true)==0);
 assert(classic_battery_percent(-1,true)==-1);
 assert(classic_battery_percent(1,true)==1);
 puts("PASS: actual curves reproduce 42/82; unplug/plug continuity, discharge, charge, full, invalid and empty readings");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(code)
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True)
 subprocess.run([str(p/'t')],check=True)
