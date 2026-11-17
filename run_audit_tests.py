from pathlib import Path
import subprocess,concurrent.futures,json,time,sys
root=Path(__file__).resolve().parent
logs=root/'verification';logs.mkdir(exist_ok=True)
jobs=[['python3',str(p.relative_to(root))] for p in sorted((root/'tests').rglob('test_*.py')) if p.name!='test_guard.py']
jobs.append(['python3','-m','unittest','discover','-s','companion','-p','test_*.py'])
def run(cmd):
 name=cmd[1] if '-m' not in cmd else 'companion-unittest'
 start=time.time();r=subprocess.run(cmd,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (logs/(name.replace('/','_')+'.log')).write_text(r.stdout)
 return {'test':name,'exit_code':r.returncode,'seconds':round(time.time()-start,2)}
prerequisite=run(['python3','tests/playlist/test_guard.py'])
if prerequisite['exit_code']:
 print('FAIL playlist harness prerequisite');sys.exit(1)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 results=[prerequisite]+list(pool.map(run,jobs))
(logs/'results.json').write_text(json.dumps(results,indent=2)+'\n')
for r in results:print(('PASS' if r['exit_code']==0 else 'FAIL'),r['test'],flush=True)
sys.exit(any(r['exit_code'] for r in results))
