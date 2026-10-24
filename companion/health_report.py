"""Read-only library checks from complete verified scan manifests.

Inspired by the reviewed rockbox-library-manager scan-safety/health patterns.
No file organization, deletion, tag changes, network requests or database writes.
Reports are replaced only when every input scan is complete and error-free.
"""
from pathlib import Path
import argparse,collections,json,os,re,tempfile,unicodedata

def load_complete(path):
    data=json.loads(Path(path).read_text())
    rows=data.get('rows',[])
    if not data.get('finished') or data.get('errors') or len(rows)!=data.get('total_files') or len(rows)!=data.get('files'):
        raise ValueError('Incomplete or failed scan; previous health report preserved: '+str(path))
    paths=[r['relative'] for r in rows]
    if len(paths)!=len(set(paths)):raise ValueError('Duplicate inventory paths')
    for r in rows:
        if len(r.get('sha256',''))!=64 or r.get('bytes',-1)<0:raise ValueError('Unverified inventory row')
    return data

def build_report(device,archive,recovery=None):
    rows=device['rows'];audio=[r for r in rows if r.get('audio')]
    paths={r['relative'] for r in rows}
    available={r['sha256'] for d in [archive,recovery] if d for r in d['rows']}
    dirs=sorted({str(Path(r['relative']).parent) for r in audio})
    missing_tags=[];artists=collections.defaultdict(set)
    for r in audio:
        tags=r.get('tags',{})
        absent=[k for k in ['artist','album','title'] if not any(str(v).strip() for v in tags.get(k,[]))]
        if absent:missing_tags.append({'file':r['relative'],'fields':absent})
        for name in tags.get('artist',[]):
            key=' '.join(unicodedata.normalize('NFKC',str(name)).casefold().split())
            artists[key].add(name)
    # Variants are suggestions; distinct guest/compilation artists stay distinct.
    variants=[sorted(v) for v in artists.values() if len(v)>1]
    return {'status':'complete read-only report','device_root':device['root'],'archive_root':archive['root'],
            'audio_tracks':len(audio),'audio_folders':len(dirs),'missing_required_tags':missing_tags,
            'missing_album_covers':[d for d in dirs if d+'/folder.jpg' not in paths],
            'missing_artist_photos':[d for d in dirs if d+'/.artist/folder.jpg' not in paths],
            'artist_spelling_or_case_variants':variants,
            'files_without_exact_verified_backup':[r['relative'] for r in audio if r['sha256'] not in available],
            'partial_download_artifacts':[r['relative'] for r in archive['rows'] if r['relative'].endswith('.parts')],
            'limits':['Hashes prove copied-file identity, not original recording quality or complete decoded audio.',
                      'No artist merging, retagging, deletion or filesystem repair is performed.',
                      'Album/artist art checks use this RodBox layout: album/folder.jpg and album/.artist/folder.jpg.',
                      'A disconnected/incomplete scan is rejected; it never means missing files should be deleted.']}

def write_report(device_path,archive_path,output,recovery_path=None):
    device=load_complete(device_path);archive=load_complete(archive_path)
    recovery=load_complete(recovery_path) if recovery_path else None
    report=build_report(device,archive,recovery)
    out=Path(output);out.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.health-',dir=out.parent)
    try:
        with os.fdopen(fd,'w') as f:
            json.dump(report,f,indent=2,ensure_ascii=False);f.flush();os.fsync(f.fileno())
        os.replace(tmp,out)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--device',required=True);p.add_argument('--archive',required=True);p.add_argument('--recovery');p.add_argument('--output',required=True)
    a=p.parse_args();r=write_report(a.device,a.archive,a.output,a.recovery)
    print(json.dumps({k:v for k,v in r.items() if k not in {'limits','device_root','archive_root'}},indent=2,ensure_ascii=False))
