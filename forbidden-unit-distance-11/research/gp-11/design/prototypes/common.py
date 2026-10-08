import os,sys,pathlib,resource,time,signal,tempfile,threading
ROOT=pathlib.Path('<repo>')
GP=ROOT/'research/gp-10'
OUT=pathlib.Path('/tmp/gp11-architect')
os.chdir(OUT)
sys.dont_write_bytecode=True
os.environ.update(PYTHONDONTWRITEBYTECODE='1',SYMPY_GROUND_TYPES='python',TMPDIR=str(OUT),SQLITE_TMPDIR=str(OUT),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
tempfile.tempdir=str(OUT)
for part in ('embed','refute','drive','check'):sys.path.insert(0,str(GP/part))
os.nice(max(0,15-os.getpriority(os.PRIO_PROCESS,0)))
resource.setrlimit(resource.RLIMIT_AS,(1024000000,1024000000))
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
MINMEM=10**12
STOP=False
class Deadline(BaseException):pass
class MemoryFloor(BaseException):pass
def memory():
 global MINMEM
 a=next(int(x.split()[1]) for x in open('/proc/meminfo') if x.startswith('MemAvailable:'))
 MINMEM=min(MINMEM,a)
 if a<1572864:raise MemoryFloor('MemAvailable below 1.5 GiB')
 return a
def monitor():
 while not STOP:
  try:memory()
  except MemoryFloor:
   (OUT/'MEMORY_STOP').write_text(str(MINMEM))
   try:
    for tid in pathlib.Path('/proc/self/task').iterdir():
     for p in (tid/'children').read_text().split():
      try:os.kill(int(p),signal.SIGKILL)
      except ProcessLookupError:pass
   finally:os.kill(os.getpid(),signal.SIGTERM)
  time.sleep(1)
def start_monitor():
 memory();threading.Thread(target=monitor,daemon=True).start()
class timer:
 def __init__(self,seconds):self.seconds=seconds
 def __enter__(self):
  self.old=signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(Deadline()))
  signal.setitimer(signal.ITIMER_REAL,self.seconds)
 def __exit__(self,*args):
  signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,self.old)
def redirect():
 for name in ('graphs','algebra','gp10refute','gp10check','msolve_exact'):
  m=sys.modules.get(name)
  if m and hasattr(m,'SCRATCH'):m.SCRATCH=OUT
 os.environ['TMPDIR']=str(OUT);os.environ['SQLITE_TMPDIR']=str(OUT);tempfile.tempdir=str(OUT)
def usage():
 return {'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'min_MemAvailable_kib':MINMEM,'cpu_self':resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,'cpu_children':resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime+resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime}
