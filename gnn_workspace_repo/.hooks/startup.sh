#!/usr/bin/env bash

set -e

# This script is always executed after the Jupyter server starts.
# Its output will show up in startup logs.
#
# Self-heal for the three known breakages every fresh env build ships
# (the channel can no longer coherently re-solve this environment):
#   1. pyarrow ABI-mismatched against azure-core-cpp   -> pip wheel overwrite
#   2. libabseil 2401 installed where torch needs 2407 -> untar staged libs
#   3. torch/version.py missing                        -> recreate stub
# Order matters: 2 needs pyarrow (dataset download), 3 needs torch importable.

PY=/home/user/envs/default/bin/python
LIB=/home/user/envs/default/lib

if ! $PY -c "import pyarrow" >/dev/null 2>&1; then
  echo "startup: pyarrow broken - overwriting with pip wheel"
  $PY -m pip install --force-reinstall --no-deps "pyarrow==17.0.0" || \
    echo "startup: pyarrow repair FAILED - run the pip command manually"
else
  echo "startup: pyarrow OK"
fi

if ! $PY -c "import torch" >/dev/null 2>&1; then
  echo "startup: torch broken - installing abseil 2407 libs from dataset"
  ABSL=$($PY -c "
from foundry.transforms import Dataset
fs = Dataset.get('gnn_training_code').files().download()
print(fs['abseil_2407_libs.tar.gz'])" 2>/dev/null | tail -1)
  if [ -n "$ABSL" ] && [ -f "$ABSL" ]; then
    tar -xzf "$ABSL" -C "$LIB/" && echo "startup: abseil libs installed"
  else
    echo "startup: abseil repair FAILED - could not fetch tarball"
  fi
fi

if $PY -c "import torch" >/dev/null 2>&1 && \
   ! $PY -c "import torch.version" >/dev/null 2>&1; then
  echo "startup: torch/version.py missing - recreating stub"
  $PY - <<'PYEOF'
import importlib.metadata as m
import os, torch
path = os.path.join(os.path.dirname(torch.__file__), "version.py")
with open(path, "w") as fh:
    fh.write(f"__version__ = '{m.version('torch')}'\n"
             "debug = False\ncuda = '12.0'\ngit_version = 'unknown'\nhip = None\n")
print("startup: wrote", path)
PYEOF
fi

$PY -c "import torch, pyarrow" >/dev/null 2>&1 \
  && echo "startup: environment healthy" \
  || echo "startup: environment STILL BROKEN - see repairs above"
