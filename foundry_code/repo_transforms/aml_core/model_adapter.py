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
    from palantir_models.io import ModelStateReader, ModelStateWriter
    _AdapterBase = pm.ModelAdapter
except ImportError:  # outside Foundry (local development / unit tests)
    pm = None
    ModelStateReader = ModelStateWriter = None
    _AdapterBase = object

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
            reverse_mp=self.config.get("reverse_mp", True),
            ego_ids=self.config.get("ego_ids", True),
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
    def predict(self, df_in: pd.DataFrame) -> pd.DataFrame:
        graph = build_graph(df_in, account_index=dict(self.account_index))
        with torch.no_grad():
            logits = self.model(
                graph.x,
                graph.edge_index,
                graph.edge_attr,
                graph.edge_index,      # score every supplied transaction
                graph.edge_attr,
            )
            proba = torch.sigmoid(logits).numpy()

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
