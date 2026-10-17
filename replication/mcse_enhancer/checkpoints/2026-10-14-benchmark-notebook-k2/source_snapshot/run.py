"""Launch this project's isolated Python with its local macOS OpenMP runtime."""
import os
from pathlib import Path
import sys

base=Path(__file__).resolve().parent
python=base/'.venv/bin/python'
if not python.exists():
    raise SystemExit('Create the MCSE .venv and install requirements-repaired.txt first.')
env=os.environ.copy()
if sys.platform=='darwin':
    libraries=list((base/'.venv/lib').glob('python*/site-packages/sklearn/.dylibs/libomp.dylib'))
    if len(libraries)!=1:
        raise SystemExit('Expected one pinned sklearn-wheel OpenMP runtime; inspect the environment.')
    env['DYLD_LIBRARY_PATH']=str(libraries[0].parent)
env['OMP_NUM_THREADS']='1'
env['OPENBLAS_NUM_THREADS']='1'
env['MKL_NUM_THREADS']='1'
os.execve(str(python),[str(python),*sys.argv[1:]],env)
