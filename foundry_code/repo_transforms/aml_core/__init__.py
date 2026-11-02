"""Shared Multi-GNN core (graph builder, model, adapter, training loop).

These module files are synced verbatim from the Code Workspace flat layout,
where they import each other by top-level name (`from graph_builder import
...`). The path shim below keeps those imports working when the files live
inside this package, so one copy of the code serves both surfaces.
"""
import os
import sys

_pkg_dir = os.path.dirname(__file__)
if _pkg_dir not in sys.path:
    sys.path.append(_pkg_dir)

from . import graph_builder, model, model_adapter, training_core  # noqa: E402,F401
