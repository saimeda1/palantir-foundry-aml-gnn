"""GPU microbenchmark: is the GPU step slow because of the GPU, or the host?

Run in a workspace terminal while training keeps going on cuda:0:

    cd ~/repo && CUDA_VISIBLE_DEVICES=1 python gpu_diag.py

Takes ~1 minute. Compares raw matmul / scatter / BatchNorm throughput with a
full AmlEdgeGNN train step on a synthetic batch of the real shape
(~120k nodes, 250k edges, 8192 seeds). T4 reference: matmul ~7 TFLOPS fp32,
full step well under 0.1s. If the full step is ~2s here too, the GPU itself
is the problem (shared/throttled/JIT); if it's fast, the slowness is in the
real loop's host side (pinned-memory allocs, transfers, syncs).
"""
import os, subprocess, sys, time

import torch

print("=== environment ===")
print("torch", torch.__version__, "| cuda", torch.version.cuda,
      "| cudnn available", torch.backends.cudnn.is_available(),
      "version", torch.backends.cudnn.version() if torch.backends.cudnn.is_available() else None)
print("device_count", torch.cuda.device_count(), "| CUDA_VISIBLE_DEVICES", os.environ.get("CUDA_VISIBLE_DEVICES"))
for i in range(torch.cuda.device_count()):
    p = torch.cuda.get_device_properties(i)
    print(f"  cuda:{i} {p.name} sm_{p.major}{p.minor} {p.total_memory/2**30:.1f}GB")
print("arch_list (needs sm_75 for T4, else PTX JIT):", torch.cuda.get_arch_list())
print("CUDA_MODULE_LOADING", os.environ.get("CUDA_MODULE_LOADING"),
      "| CUDA_CACHE_DISABLE", os.environ.get("CUDA_CACHE_DISABLE"))
try:
    out = subprocess.run(["nvidia-smi", "--query-gpu=index,name,utilization.gpu,clocks.sm,clocks.max.sm,"
                          "memory.used,memory.total,power.draw,pstate,clocks_throttle_reasons.active",
                          "--format=csv"], capture_output=True, text=True, timeout=20)
    print("nvidia-smi:\n" + (out.stdout or out.stderr))
    out = subprocess.run(["nvidia-smi", "--query-compute-apps=gpu_uuid,pid,process_name,used_memory",
                          "--format=csv"], capture_output=True, text=True, timeout=20)
    print("compute apps:\n" + (out.stdout or out.stderr))
except Exception as e:  # noqa
    print("nvidia-smi unavailable:", e)
sys.stdout.flush()

dev = torch.device("cuda")


def bench(label, fn, n=10):
    fn(); torch.cuda.synchronize()          # warmup (JIT, cuBLAS handles)
    t = time.time()
    for _ in range(n):
        fn()
    torch.cuda.synchronize()
    dt = (time.time() - t) / n
    print(f"{label}: {dt*1000:.1f} ms"); sys.stdout.flush()
    return dt


print("\n=== kernel launch latency (a train step issues a few hundred launches) ===")
one = torch.zeros(1, device=dev)
dt = bench("1000 tiny launches (add_ on 1 element)", lambda: [one.add_(1) for _ in range(1000)], n=3)
print(f"  -> {dt*1e6/1000:.0f} us per launch (bare metal ~5-10us; >200us means every "
      f"launch is trapped/serialised: hypervisor, CUDA_LAUNCH_BLOCKING, or GIL starvation)")
print("CUDA_LAUNCH_BLOCKING", os.environ.get("CUDA_LAUNCH_BLOCKING"))

print("\n=== raw kernels ===")
a = torch.randn(4096, 4096, device=dev)
dt = bench("matmul 4096^2 fp32", lambda: a @ a)
print(f"  -> {2*4096**3/dt/1e12:.1f} TFLOPS (T4 ~7)")
N, E, H = 120_000, 250_000, 64
h = torch.randn(N, H, device=dev); idx = torch.randint(0, N, (E,), device=dev)
msg = torch.randn(E, H, device=dev)
bench("scatter_add 250k x64 -> 120k", lambda: h.new_zeros(N, H).index_add_(0, idx, msg))
bn = torch.nn.BatchNorm1d(H).to(dev)
bench("BatchNorm1d 250k x64", lambda: bn(msg))
lin = torch.nn.Linear(H, H).to(dev)
bench("Linear 250k x64", lambda: lin(msg))

print("\n=== host <-> device ===")
cpu = torch.randn(E, 30)
bench("H2D 30MB pageable", lambda: cpu.to(dev, non_blocking=True))
bench("pin_memory() 30MB fresh tensor", lambda: torch.randn(E, 30).pin_memory(), n=5)
pinned = cpu.pin_memory()
bench("H2D 30MB pinned", lambda: pinned.to(dev, non_blocking=True))

print("\n=== full AmlEdgeGNN step, synthetic batch of the real shape ===")
from model import AmlEdgeGNN, focal_loss
from graph_builder import EDGE_FEATURE_DIM, NODE_FEATURE_DIM
model = AmlEdgeGNN(node_dim=NODE_FEATURE_DIM, edge_dim=EDGE_FEATURE_DIM, hidden_dim=64,
                   num_layers=2, reverse_mp=True, ego_ids=True).to(dev)
opt = torch.optim.AdamW(model.parameters(), 1e-3)
x = torch.randn(N, NODE_FEATURE_DIM, device=dev)
ei = torch.randint(0, N, (2, E), device=dev)
ea = torch.randn(E, EDGE_FEATURE_DIM, device=dev)
B = 8192
eli = torch.randint(0, N, (2, B), device=dev)
sea = torch.randn(B, EDGE_FEATURE_DIM, device=dev)
y = (torch.rand(B, device=dev) < 0.001).float()

model.train()
bench("forward only", lambda: model(x, ei, ea, eli, sea))


def step():
    opt.zero_grad(set_to_none=True)
    loss = focal_loss(model(x, ei, ea, eli, sea), y, alpha=0.95, gamma=2.0)
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    opt.step()
    return float(loss.detach())


bench("forward+backward+clip+AdamW (+sync)", step)
print("\ndone")
