import sys,ast
from pathlib import Path
sys.path.insert(0,'<repo>/research/gp-11/pipeline')
import test_history
source=ast.parse(Path('/tmp/gp11-build/baseline-store.py').read_text())
cls=next(n for n in source.body if isinstance(n,ast.ClassDef) and n.name=='Store')
method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='unknown_record')
namespace={}
exec(compile(ast.Module(body=[method],type_ignores=[]),'<baseline unknown_record>','exec'),test_history.__dict__,namespace)
test_history.Store.unknown_record=namespace['unknown_record']
sys.argv=['test_history.py','--index','/tmp/gp11-pipeline-index','--output','/tmp/gp11-build/history-baseline']
test_history.main()
