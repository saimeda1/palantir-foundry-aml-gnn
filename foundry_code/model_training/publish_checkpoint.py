"""Publish a previously trained + checkpointed adapter without retraining.

    cd ~/repo && python publish_checkpoint.py aml_gnn_hi_small [path/to.pt]

Default checkpoint path: ~/repo/checkpoints/<alias>.pt (written by
train_gnn_foundry.py right before it publishes). Requires the alias to exist
in the Models sidebar (.foundry/model-assets.yml).
"""
import os
import sys

import train_gnn_foundry as t


def main():
    alias = sys.argv[1] if len(sys.argv) > 1 else t.MODEL_ALIAS
    path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(t.CKPT_DIR, f"{alias}.pt")
    if not os.path.exists(path):
        raise SystemExit(f"no checkpoint at {path}")
    output = t.resolve_model_output(alias)
    adapter, metrics = t.load_checkpoint(path)
    print(f"loaded {path} | {metrics}")
    output.publish(adapter)
    print(f"published model alias '{alias}'")
    return adapter


if __name__ == "__main__":
    main()
