# AIP Logic — SAR Draft Assistant

AIP Logic function `draft_sar_narrative`, wired into the Workshop Alert
Detail and Case Workbench pages. Human-in-the-loop: output is a **draft**
saved to `InvestigationCase.analyst_notes` staging, never auto-filed.

## Function inputs (Logic board)
1. `case` (InvestigationCase object) or `alert` (Alert object)
2. Ontology traversals executed by Logic *before* the LLM block, so the
   model only sees retrieved facts:
   - Alerts in case → Transactions (`concerns`) → RiskScores (`has_score`)
   - Sender/receiver Accounts (`sent` / `received_by`) with 24h volumes
   - 2-hop counterparty transactions within ±72h window, capped at 200 edges
3. Analyst free-text observations (optional Workshop input).

## Prompt template (LLM block)

```
You are an AML compliance drafting assistant. Using ONLY the structured
facts below, draft a Suspicious Activity Report narrative for review by a
licensed BSA/AML analyst. Do not invent entities, amounts, dates, or
typologies not present in the facts. Where evidence is weak, say so.

=== CASE FACTS ===
Case: {{case.case_id}} | Status: {{case.case_status}}
Alerts: {{formatted_alert_table}}          // id, priority, band, probability, typology
Flagged transactions: {{formatted_txn_table}}  // id, ts, from, to, amount_usd, format
Subject accounts: {{formatted_account_table}}  // id, bank, 24h in/out volume, max risk
Counterparty network (2-hop, ±72h): {{formatted_network_summary}}
Model: {{model_version}}; probabilities are GNN edge-classification scores.
Analyst observations: {{analyst_observations}}

=== REQUIRED OUTPUT (markdown) ===
1. **Subject & account summary** — who, where, aggregate 24h flows.
2. **Suspicious activity narrative** — chronological description of the
   flagged flows; name the apparent typology (e.g., structuring, layering,
   fan-in/fan-out, round-tripping) only if the transaction pattern in the
   facts supports it, citing transaction ids.
3. **Supporting model evidence** — risk scores and bands, with the caveat
   that scores are investigative leads, not conclusions.
4. **Gaps & recommended next steps** — missing KYC data, additional
   accounts to review.
5. **Draft disposition** — one of: "SAR recommended", "Continue monitoring",
   "Close as false positive", with one-paragraph justification.
```

## Guardrails
- Logic block temperature low; retrieval capped; no tool/web access.
- Output rendered in Workshop side-by-side with the Vertex graph for
  verification; analyst must edit-and-approve before `sar_required` can be
  set to true (submission criterion on the case action).
- Every generation logged with model version + input snapshot for audit.
