"""Workspace diagnostic: where does training time go?  Run in a terminal:

    cd ~/repo && python diag_loader.py            # HI-Small, batch 8192

Prints CPU/thread topology, then times graph build, serial sampling,
threaded sampling (4/8 threads), and a full GPU train step, so the
bottleneck is visible instead of guessed. Takes ~3-4 minutes.
"""
import os, sys, time

import torch

print("=== topology ===")
print("os.cpu_count:", os.cpu_count())
try:
    print("sched_getaffinity:", len(os.sched_getaffinity(0)))
except AttributeError:
    pass
for f in ("/sys/fs/cgroup/cpu.max", "/sys/fs/cgroup/cpu/cpu.cfs_quota_us",
          "/sys/fs/cgroup/cpu/cpu.cfs_period_us"):
    if os.path.exists(f):
        print(f, "=", open(f).read().strip())
print("torch.get_num_threads:", torch.get_num_threads(),
      "| interop:", torch.get_num_interop_threads())
print("OMP_NUM_THREADS:", os.environ.get("OMP_NUM_THREADS"),
      "MKL_NUM_THREADS:", os.environ.get("MKL_NUM_THREADS"))
print("cuda:", torch.cuda.is_available(),
      torch.cuda.get_device_name(0) if torch.cuda.is_available() else "")
import torch_geometric.typing as T
print("pyg_lib:", T.WITH_PYG_LIB, "torch_sparse:", T.WITH_TORCH_SPARSE)
sys.stdout.flush()

from foundry.transforms import Dataset
from graph_builder import build_graph
from training_core import make_loader
from model import AmlEdgeGNN, focal_loss
from graph_builder import EDGE_FEATURE_DIM, NODE_FEATURE_DIM

t = time.time()
df = Dataset.get("raw_transactions_train").read_table(format="pandas")
print(f"\nread train: {len(df):,} rows in {time.time()-t:.0f}s"); t = time.time()
g = build_graph(df); del df
print(f"build_graph: {g.num_nodes:,} nodes {g.edge_index.size(1):,} edges in {time.time()-t:.0f}s")
sys.stdout.flush()

BATCH, FANOUT, N = 8192, [15, 10], 10


def time_loader(threads, label):
    loader = make_loader(g, BATCH, FANOUT, True, threads, False)
    it = iter(loader)
    next(it)                      # exclude first-batch setup
    t = time.time()
    for _ in range(N):
        next(it)
    dt = (time.time() - t) / N
    print(f"{label}: {dt:.3f}s/batch -> ~{dt*len(loader)/60:.1f} min/epoch sampling only")
    sys.stdout.flush()
    return dt


print("\n=== sampling, intra-op threads =", torch.get_num_threads(), "===")
time_loader(0, "serial")
time_loader(4, "4 threads")
time_loader(8, "8 threads")

n_phys = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count()
if torch.get_num_threads() != n_phys:
    torch.set_num_threads(n_phys)
    print(f"\n=== sampling, intra-op threads pinned to {n_phys} ===")
    time_loader(0, "serial")
    time_loader(8, "8 threads")

if torch.cuda.is_available():
    print("\n=== full train step on GPU (serial loader) ===")
    dev = torch.device("cuda")
    model = AmlEdgeGNN(node_dim=NODE_FEATURE_DIM, edge_dim=EDGE_FEATURE_DIM, hidden_dim=64,
                       num_layers=2, reverse_mp=True, ego_ids=True).to(dev)
    opt = torch.optim.AdamW(model.parameters(), 1e-3)
    loader = make_loader(g, BATCH, FANOUT, True, 0, True)
    it = iter(loader)
    sample_t = compute_t = 0.0
    for i in range(N + 1):
        t0 = time.time(); b = next(it); t1 = time.time()
        seed_attr = g.edge_attr[b.input_id].to(dev, non_blocking=True)
        b = b.to(dev, non_blocking=True)
        opt.zero_grad(set_to_none=True)
        logits = model(b.x, b.edge_index, b.edge_attr, b.edge_label_index, seed_attr)
        loss = focal_loss(logits, b.edge_label.float(), alpha=0.95, gamma=2.0)
        loss.backward(); opt.step(); torch.cuda.synchronize(); t2 = time.time()
        if i > 0:                 # skip warmup batch
            sample_t += t1 - t0; compute_t += t2 - t1
    print(f"sampling {sample_t/N:.3f}s/batch | gpu step {compute_t/N:.3f}s/batch | "
          f"total ~{(sample_t+compute_t)/N*len(loader)/60:.1f} min/epoch")
print("\ndone")
