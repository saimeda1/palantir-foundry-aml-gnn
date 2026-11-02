"""Publish the HI-Small checkpoint stored in the `aml_model_checkpoints`
dataset to the `aml_gnn_hi_small` model. Written to run as a Code Workspaces
transform ("Publish as transform output" on the model card), i.e. as a
Foundry build with build permissions, because the interactive workspace
session's token is denied artifact writes on this enrollment
(Artifacts:WriteArtifactPermissionDenied). Also runnable interactively.

Transform config: input alias `aml_model_checkpoints`, output alias
`aml_gnn_hi_small`.
"""
import os

from foundry.transforms import Dataset

import train_gnn_foundry as t

CKPT_ALIAS = os.environ.get("AML_CKPT_ALIAS", "aml_model_checkpoints")
CKPT_FILE = os.environ.get("AML_CKPT_FILE", "aml_gnn_hi_small.pt")
MODEL_ALIAS = os.environ.get("AML_MODEL_ALIAS", "aml_gnn_hi_small")


def main():
    files = Dataset.get(CKPT_ALIAS).files().download()
    path = files[CKPT_FILE]
    print(f"checkpoint downloaded: {path} ({os.path.getsize(path):,} bytes)")
    adapter, metrics = t.load_checkpoint(path)
    print(f"loaded | {metrics}")
    output = t.resolve_model_output(MODEL_ALIAS)
    output.publish(adapter)
    print(f"published model alias '{MODEL_ALIAS}'")
    return adapter


if __name__ == "__main__":
    main()
