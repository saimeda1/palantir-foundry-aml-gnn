# AML Investigator Workshop — Layout Plan

Application: **AML Investigator Console** (Workshop, backed by the ontology in
`ontology/aml_ontology.yml`).

## Page 1 — Alert Inbox
- **Header KPI row** (metric cards): Open alerts, P1 open, alerts opened last 24h,
  median time-to-triage, High-band precision (vs. `is_laundering_ground_truth`
  while running on the labeled test stream).
- **Filter bar**: status, priority, risk_band, alerted_ts range, bank_id.
- **Object table** (Alert, default sort `laundering_probability` desc):
  alert_id, priority, risk_band, laundering_probability, primary_typology,
  subject_account_id, alerted_ts, status.
- **Inline actions**: `triageAlert`, `closeFalsePositive`; multi-select →
  `escalateToCase`.
- Row click → sets selected-Alert variable → navigates to Page 2.

## Page 2 — Alert Detail & Network (Vertex)
- **Left panel**: Alert properties + linked `TransactionRiskScore`
  (probability, band, model_version) + linked Transaction details.
- **Center**: **Vertex graph widget** seeded on the alert's Transaction:
  - Expand: `sent` / `received_by` links to Accounts, then 2 hops of each
    account's transactions within ±72h of the alerted transaction.
  - Node color: Account by `max_risk_score` gradient; edge width: amount_usd;
    edge color: risk_band (High=red, Medium=amber, Low=grey).
  - Layout preset saved so cyclical flows (round-tripping, fan-in/fan-out
    structuring patterns) are visually obvious.
- **Right panel**: AIP Assistant widget (see `aip_sar_prompt.md`) with
  "Summarize network" and "Draft SAR" buttons.
- **Footer**: action buttons `triageAlert`, `escalateToCase`, `closeFalsePositive`.

## Page 3 — Account 360
- **Header**: account_id, bank_id, max_risk_score badge.
- **Metric cards**: `volume_24h_inbound`, `volume_24h_outbound`,
  inbound/outbound ratio, counterparty count, open alerts touching account.
- **Time series chart**: daily in/out volume with High-band transactions
  overlaid as markers.
- **Object table**: all transactions where account is sender or receiver
  (union via two filtered tables in tabs), each row linking to its score.
- **Related alerts & cases section**: Alert table filtered by
  `subject_account_id`, linked InvestigationCases.

## Page 4 — Case Workbench
- InvestigationCase list + detail: aggregated alerts table, combined Vertex
  view seeded from all case alerts, `analyst_notes` editor (Action-backed),
  `sar_required` toggle, SAR draft document panel populated by the AIP logic
  function, case status workflow buttons.

## Variables & state
- `selectedAlert`, `selectedAccount`, `selectedCase` shared across pages.
- All state changes flow through the three Action types so the audit log in
  Foundry captures every investigator decision.
