"""Palantir ModelAdapter wrapping the trained AML GNN.

Published to /AML_Compliance_Platform/02_Models/aml_gnn_model. The adapter
accepts a batch dataframe of raw transactions and returns
laundering_probability and risk_band per transaction, so it can back both
the batch scoring transform and a live deployment.
"""
from __future__ import annotations

import json

import pandas as pd
import torch

try:
    import palantir_models as pm
except ImportError:  # outside Foundry (local development / unit tests)
    pm = None
    _AdapterBase = object
else:
    # NOTE: never guard anything else in this try - a failed secondary
    # import once made the adapter silently inherit from `object`, and
    # publish failed with "'AmlGnnAdapter' object has no attribute '_api'".
    _AdapterBase = pm.ModelAdapter

from graph_builder import EDGE_FEATURE_DIM, NODE_FEATURE_DIM, build_graph
from model import AmlEdgeGNN

_INPUT_COLUMNS = [
    ("transaction_id", int),
    ("timestamp", str),
    ("from_bank", str),
    ("from_account", str),
    ("to_bank", str),
    ("to_account", str),
    ("amount_received", float),
    ("receiving_currency", str),
    ("amount_paid", float),
    ("payment_currency", str),
    ("payment_format", str),
]


class AmlGnnAdapter(_AdapterBase):
    def __init__(self, state_dict=None, account_index=None, thresholds=None,
                 config=None):
        self.config = config or {}
        self.account_index = account_index or {}
        self.thresholds = thresholds or {"high": 0.85, "medium": 0.5}
        self.model = AmlEdgeGNN(
            node_dim=self.config.get("node_dim", NODE_FEATURE_DIM),
            edge_dim=self.config.get("edge_dim", EDGE_FEATURE_DIM),
            hidden_dim=self.config.get("hidden_dim", 64),
            num_layers=self.config.get("num_layers", 2),
            reverse_mp=self.config.get("reverse_mp", True),
            ego_ids=self.config.get("ego_ids", True),
            edge_updates=self.config.get("edge_updates", False),
        )
        if state_dict is not None:
            self.model.load_state_dict(state_dict)
        self.model.eval()

    # ------------------------------------------------------- serialization
    def save(self, state_writer) -> None:
        with state_writer.open("weights.pt", "wb") as fh:
            torch.save(self.model.state_dict(), fh)
        with state_writer.open("metadata.json", "w") as fh:
            json.dump(
                {
                    "config": self.config,
                    "thresholds": self.thresholds,
                    "account_index": self.account_index,
                },
                fh,
            )

    @classmethod
    def load(cls, state_reader) -> "AmlGnnAdapter":
        with state_reader.open("metadata.json", "r") as fh:
            meta = json.load(fh)
        with state_reader.open("weights.pt", "rb") as fh:
            state_dict = torch.load(fh, map_location="cpu")
        return cls(
            state_dict=state_dict,
            account_index=meta["account_index"],
            thresholds=meta["thresholds"],
            config=meta["config"],
        )

    # --------------------------------------------------------------- api
    @classmethod
    def api(cls):
        columns = [(name, dtype) for name, dtype in _INPUT_COLUMNS]
        inputs = {"df_in": pm.Pandas(columns=columns)}
        outputs = {
            "df_out": pm.Pandas(
                columns=columns
                + [("laundering_probability", float), ("risk_band", str)]
            )
        }
        return inputs, outputs

    # ----------------------------------------------------------- predict
    def predict(self, df_in: pd.DataFrame,
                history_df: pd.DataFrame | None = None,
                batch_size: int = 8192) -> pd.DataFrame:
        """Score every transaction in df_in. history_df (older transactions,
        NOT scored) extends the message-passing graph so accounts keep their
        history -- thin-neighborhood scoring misses patterns the model was
        trained to see.

        Inference replicates the TRAINING/VALIDATION protocol exactly: seeds
        are scored in batches through a LinkNeighborLoader with the same
        per-hop fanout, so (a) hub accounts see the same truncated
        neighborhoods the BatchNorm statistics were fitted on and (b) ego-ID
        flags mark only the current batch's seed endpoints, as in training.
        Whole-graph single-pass inference breaks both and silently degrades
        scores."""
        from torch_geometric.loader import LinkNeighborLoader

        feature_cols = [name for name, _ in _INPUT_COLUMNS if name != "transaction_id"]
        if history_df is not None and len(history_df):
            df_all = pd.concat(
                [history_df[feature_cols], df_in[feature_cols]], ignore_index=True
            )
            n_hist = len(history_df)
        else:
            df_all, n_hist = df_in[feature_cols], 0

        graph = build_graph(df_all, account_index=dict(self.account_index))
        seeds = torch.arange(n_hist, n_hist + len(df_in))
        seed_attr_store = graph.edge_attr[seeds]
        fanout = list(self.config.get("num_neighbors", [50, 30]))
        loader = LinkNeighborLoader(
            graph,
            num_neighbors=fanout,
            edge_label_index=graph.edge_index[:, seeds],
            edge_label=torch.zeros(len(seeds)),
            batch_size=batch_size,
            shuffle=False,
            num_workers=0,
            filter_per_worker=True,
        )
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = self.model.to(device).eval()
        proba = torch.empty(len(seeds))
        with torch.no_grad():
            for batch in loader:
                seed_attr = seed_attr_store[batch.input_id].to(device)
                batch = batch.to(device)
                logits = model(
                    batch.x, batch.edge_index, batch.edge_attr,
                    batch.edge_label_index, seed_attr,
                )
                proba[batch.input_id] = torch.sigmoid(logits.float()).cpu()
        proba = proba.numpy()

        out = df_in.copy()
        out["laundering_probability"] = proba
        high, med = self.thresholds["high"], self.thresholds["medium"]
        out["risk_band"] = pd.cut(
            out["laundering_probability"],
            bins=[-float("inf"), med, high, float("inf")],
            labels=["Low", "Medium", "High"],
        ).astype(str)
        return out

    def run_inference(self, inputs, outputs):
        outputs.df_out.write(self.predict(inputs.df_in.read()))
