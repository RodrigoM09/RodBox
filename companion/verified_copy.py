"""Verified atomic copying for local removable-media backups.

Independently written implementation of patterns reviewed in HifiMule:
https://github.com/HifiMule/HifiMule (device_io.rs/checkpoint.rs).
No automatic deletion or destination discovery. Callers own explicit plans,
backup old versions before replacement, and record checkpoints after success.
"""
from pathlib import Path
import fcntl,hashlib,os,sys,uuid

def contained(root,relative):
    root=Path(root).resolve(strict=True)
    rel=Path(relative)
    if rel.is_absolute() or not rel.parts or any(p in {'.','..'} for p in rel.parts):
        raise ValueError('Expected a nonempty contained relative path')
    p=root/rel
    # Reject symlinks even when their current target happens to be contained.
    item=root
    for component in rel.parts:
        item=item/component
        if item.is_symlink():raise ValueError('Symlink in copy path: '+str(item))
    resolved=p.resolve()
    if not resolved.is_relative_to(root.resolve()):raise ValueError('Path escapes root')
    return p

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        if sys.platform=='darwin':fcntl.fcntl(f.fileno(),48,1)
        while block:=f.read(1024*1024):h.update(block)
    return h.hexdigest()

def copy_verified(source_root,source_relative,dest_root,dest_relative,expected_sha256,
                  expected_size,*,expected_old_sha256=None,identity=None,cancel=None):
    src=contained(source_root,source_relative)
    dst=contained(dest_root,dest_relative)
    if src.resolve()==dst.resolve():raise ValueError('Source equals destination')
    if identity:identity()
    before=src.stat()
    if before.st_size!=expected_size:raise ValueError('Source size changed')
    old_exists=dst.exists()
    if old_exists:
        current=digest(dst)
        if current==expected_sha256 and dst.stat().st_size==expected_size:
            return {'status':'already verified','sha256':current,'bytes':expected_size}
        if expected_old_sha256 is None or current!=expected_old_sha256:
            raise FileExistsError('Existing destination differs from approved replacement')
    elif expected_old_sha256 is not None:raise FileNotFoundError('Expected old destination missing')
    dst.parent.mkdir(parents=True,exist_ok=True)
    contained(dest_root,dest_relative)
    temp=dst.with_name('.rodbox-copy-'+uuid.uuid4().hex)
    try:
        h=hashlib.sha256();copied=0
        with src.open('rb') as f,temp.open('xb') as out:
            if sys.platform=='darwin':
                fcntl.fcntl(f.fileno(),48,1);fcntl.fcntl(out.fileno(),48,1)
            while block:=f.read(1024*1024):
                if cancel and cancel():raise InterruptedError('Copy cancelled')
                assert out.write(block)==len(block)
                h.update(block);copied+=len(block)
            out.flush();os.fsync(out.fileno())
            if sys.platform=='darwin':
                # Unsupported full-sync is not silently treated as verified.
                fcntl.fcntl(out.fileno(),51)
        after=src.stat()
        if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns):
            raise ValueError('Source changed during copy')
        if copied!=expected_size or h.hexdigest()!=expected_sha256:raise ValueError('Source checksum mismatch')
        if digest(temp)!=expected_sha256:raise OSError('Temporary file verification failed')
        if identity:identity()
        if cancel and cancel():raise InterruptedError('Copy cancelled before commit')
        contained(dest_root,dest_relative)
        if old_exists:
            if not dst.exists() or digest(dst)!=expected_old_sha256:raise ValueError('Destination changed during copy')
        elif dst.exists():raise FileExistsError('Destination appeared during copy')
        os.replace(temp,dst)
        if digest(dst)!=expected_sha256:raise OSError('Committed file verification failed')
        return {'status':'copied and verified','sha256':expected_sha256,'bytes':copied}
    finally:
        if temp.exists():temp.unlink()
