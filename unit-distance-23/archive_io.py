"""Read a hash-bound evidence archive without expanding it onto disk."""
import builtins, fnmatch, gzip, hashlib, io, json, os, re, stat, subprocess, tarfile
from contextlib import contextmanager
from pathlib import Path

def gz(data):
    out=io.BytesIO()
    with gzip.GzipFile(filename='',fileobj=out,mode='wb',compresslevel=6,mtime=0) as f:f.write(data)
    return out.getvalue()
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
@contextmanager
def mount(root,archive):
    root=Path(root).resolve();archive=Path(archive).resolve()
    expected=json.loads((root/'EVIDENCE-FILE.json').read_text())
    if archive.stat().st_size!=expected['bytes'] or sha(archive)!=expected['sha256']:raise ValueError('evidence archive bytes or sha256 differ')
    proc=subprocess.Popen(['zstd','-q','-d','-c',str(archive)],stdout=subprocess.PIPE)
    payloads={};index=None;previous=''
    try:
        with tarfile.open(fileobj=proc.stdout,mode='r|') as t:
            for member in t:
                if not member.isfile() or member.name<=previous or member.uid or member.gid or member.uname or member.gname or member.mtime or member.mode!=0o644:raise ValueError('unsafe or noncanonical archive member')
                previous=member.name
                if member.name=='zz-archive-index.json':index=json.load(t.extractfile(member));continue
                if not re.fullmatch(r'data/\d{8}',member.name):raise ValueError('unexpected archive member')
                raw=t.extractfile(member).read();payloads[member.name]=(gz(raw),len(raw),hashlib.sha256(raw).hexdigest())
        proc.stdout.close()
        if proc.wait()!=0:raise ValueError('evidence archive decompression failed')
    finally:
        if proc.poll() is None:proc.kill();proc.wait()
    if not index or index.get('format')!='aw-evidence-v2' or index['slug']!=root.name or index['researchCommit']!=expected['researchCommit']:raise ValueError('evidence archive identity differs')
    mem={}
    for item in index['members']:
        p=Path(item['public'])
        if p.is_absolute() or '..' in p.parts or str(p) in mem:raise ValueError('unsafe or duplicate logical archive path')
        comp,n,actual=payloads.pop(item['member'])
        if n!=item['bytes'] or actual!=item['sha256']:raise ValueError('archive member source binding differs')
        public=comp if item['gzip'] else gzip.decompress(comp)
        if hashlib.sha256(public).hexdigest()!=item['publicSha256']:raise ValueError('archive public representation differs')
        if (root/p).is_file():
            if hashlib.sha256((root/p).read_bytes()).hexdigest()!=item['publicSha256']:raise ValueError('shared GitHub/archive summary differs '+str(p))
            continue
        mem[str(p)]=(comp,item['gzip'],len(public))
    if payloads:raise ValueError('unindexed archive data')
    for p,value in index['virtualJSON'].items():
        if p!='PUBLICATION-TRANSFORMS.json':raise ValueError('unexpected generated archive metadata')
        raw=(json.dumps(value,separators=(',',':'),ensure_ascii=False)+'\n').encode();mem[p]=(gz(raw),False,len(raw))
    originals={name:getattr(Path,name) for name in ['open','read_bytes','read_text','exists','is_file','is_dir','stat','glob']};old_open=builtins.open
    def relative(p):
        try:return Path(os.path.realpath(os.fspath(p))).relative_to(root).as_posix()
        except (ValueError,TypeError):return None
    def body(rel):
        comp,isgz,n=mem[rel];return comp if isgz else gzip.decompress(comp)
    def opened(p,mode='r',*args,**kwargs):
        rel=relative(p)
        if rel not in mem:return old_open(p,mode,*args,**kwargs)
        if any(x in mode for x in 'wax+'):raise ValueError('archive evidence is read only')
        data=io.BytesIO(body(rel))
        if 'b' in mode:return data
        encoding=kwargs.get('encoding') or (args[1] if len(args)>1 else None) or 'utf8'
        return io.TextIOWrapper(data,encoding=encoding,errors=kwargs.get('errors'),newline=kwargs.get('newline'))
    def directory(p):
        rel=relative(p);return rel is not None and any(k.startswith(rel.rstrip('/')+'/') for k in mem)
    def exists(p):return relative(p) in mem or directory(p) or originals['exists'](p)
    def isfile(p):return relative(p) in mem or originals['is_file'](p)
    def isdir(p):return directory(p) or originals['is_dir'](p)
    def statistics(p,*args,**kwargs):
        rel=relative(p)
        if rel in mem:return os.stat_result((stat.S_IFREG|0o444,0,0,1,0,0,mem[rel][2],0,0,0))
        if directory(p) and not os.path.exists(os.fspath(p)):return os.stat_result((stat.S_IFDIR|0o555,0,0,1,0,0,0,0,0,0))
        return originals['stat'](p,*args,**kwargs)
    def glob(p,pattern,*args,**kwargs):
        found=set(originals['glob'](p,pattern,*args,**kwargs));rel=relative(p)
        if rel is not None:
            prefix='' if rel=='.' else rel.rstrip('/')+'/'
            candidates=set()
            for key in mem:
                if not key.startswith(prefix):continue
                tail=key[len(prefix):];parts=tail.split('/')
                candidates.update('/'.join(parts[:i]) for i in range(1,len(parts)+1))
            for tail in candidates:
                # A plain glob component does not cross a directory boundary.
                if '/' not in pattern and '/' in tail:continue
                if fnmatch.fnmatchcase(tail,pattern):found.add(root/(prefix+tail))
        yield from sorted(found)
    Path.open=lambda p,mode='r',*a,**k:opened(p,mode,*a,**k)
    Path.read_bytes=lambda p:body(relative(p)) if relative(p) in mem else originals['read_bytes'](p)
    Path.read_text=lambda p,*a,**k:opened(p,'r',encoding=k.get('encoding') or (a[0] if a else None),errors=k.get('errors')).read() if relative(p) in mem else originals['read_text'](p,*a,**k)
    Path.exists=exists;Path.is_file=isfile;Path.is_dir=isdir;Path.stat=statistics;Path.glob=glob;builtins.open=opened
    print(f'Evidence archive verified: {len(mem)} logical files; read-only memory view, no disk expansion',flush=True)
    try:yield mem
    finally:
        for name,fn in originals.items():setattr(Path,name,fn)
        builtins.open=old_open
