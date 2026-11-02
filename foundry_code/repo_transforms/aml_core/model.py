"""AML edge-classification GNN implementing the Multi-GNN adaptations
(Egressy et al., AAAI 2024) on a GINE backbone:

- reverse message passing: every layer runs a second GINEConv over flipped
  edges with its own weights, so pattern context flows both with and
  against transaction direction (fan-out is visible from the source side).
- ego IDs: seed-edge endpoints get a marker feature per sampled batch
  (batched variant: all seed endpoints in the batch are flagged), enabling
  directed-cycle detection back to the seed.
- port numbering arrives via edge features from graph_builder.py.
"""
from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn
from torch_geometric.nn import GINEConv


def focal_loss(logits: torch.Tensor, targets: torch.Tensor,
               alpha: float = 0.95, gamma: float = 2.0) -> torch.Tensor:
    """Binary focal loss for the ~0.1% positive laundering class."""
    bce = F.binary_cross_entropy_with_logits(logits, targets, reduction="none")
    p_t = torch.exp(-bce)
    alpha_t = alpha * targets + (1.0 - alpha) * (1.0 - targets)
    return (alpha_t * (1.0 - p_t) ** gamma * bce).mean()


def _gine(hidden_dim: int) -> GINEConv:
    mlp = nn.Sequential(
        nn.Linear(hidden_dim, hidden_dim),
        nn.ReLU(),
        nn.Linear(hidden_dim, hidden_dim),
    )
    return GINEConv(mlp, edge_dim=hidden_dim)


class AmlEdgeGNN(nn.Module):
    """Bidirectional GINEConv stack + edge head scoring each seed
    transaction from [h_src, h_dst, encoded edge features]."""

    def __init__(self, node_dim: int, edge_dim: int, hidden_dim: int = 64,
                 num_layers: int = 2, dropout: float = 0.1,
                 reverse_mp: bool = True, ego_ids: bool = True):
        super().__init__()
        self.reverse_mp = reverse_mp
        self.ego_ids = ego_ids
        self.node_encoder = nn.Linear(node_dim + (1 if ego_ids else 0), hidden_dim)
        self.edge_encoder = nn.Linear(edge_dim, hidden_dim)
        self.convs_fwd = nn.ModuleList(_gine(hidden_dim) for _ in range(num_layers))
        self.convs_bwd = (
            nn.ModuleList(_gine(hidden_dim) for _ in range(num_layers))
            if reverse_mp else None
        )
        self.dropout = dropout
        self.head = nn.Sequential(
            nn.Linear(3 * hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, x, edge_index, edge_attr, edge_label_index, seed_edge_attr):
        """
        x, edge_index, edge_attr: the sampled subgraph (message passing).
        edge_label_index: [2, B] endpoints (local ids) of seed transactions.
        seed_edge_attr:   [B, edge_dim] raw features of the seed transactions.
        """
        if self.ego_ids:
            flag = x.new_zeros(x.size(0), 1)
            flag[edge_label_index.reshape(-1)] = 1.0
            x = torch.cat([x, flag], dim=-1)

        h = self.node_encoder(x)
        e = self.edge_encoder(edge_attr)
        rev_index = edge_index.flip(0) if self.reverse_mp else None
        for i, conv in enumerate(self.convs_fwd):
            out = conv(h, edge_index, e)
            if self.reverse_mp:
                out = out + self.convs_bwd[i](h, rev_index, e)
            h = F.relu(out)
            h = F.dropout(h, p=self.dropout, training=self.training)

        src, dst = edge_label_index
        seed_e = self.edge_encoder(seed_edge_attr)
        z = torch.cat([h[src], h[dst], seed_e], dim=-1)
        return self.head(z).squeeze(-1)
