# AML Investigator — Ontology, Vertex & Workshop build guide

**Status 2026-10-29:** model published, test stream scored, all seven backing datasets live in
`/AML_Compliance_Platform/03_Scored_Data` with schemas. This guide turns them into the
investigator surface. Everything below is UI work in Foundry; every dataset, column and value
named here exists exactly as written (source of truth: `ontology/aml_ontology.yml` v2).

Time estimate: Ontology Manager 45 min · Vertex 20 min · Workshop 2–3 h · AIP Logic 45 min.

---

## 0. Before you start

- Object types go in a new ontology namespace (or your default one), API-name prefix `aml`.
- Mark these as **edits-enabled** object types: **Alert** and **InvestigationCase** (actions
  modify them). The rest are read-only.
- Three columns are **ground truth for the demo reveal** and must be hidden from investigator
  pages: `Transaction.is_laundering_ground_truth`, `Alert.pattern_id`, `Alert.true_typology`,
  `Alert.is_laundering_ground_truth`. Keep them in the ontology (the evaluation page uses them)
  but not in Workshop triage widgets.

## 1. Ontology Manager — object types

Create each from its dataset (**New object type → from dataset**), set primary key and title,
accept inferred property types, then apply the display names below.

| Object type (API name) | Dataset | Primary key | Title | Notes |
|---|---|---|---|---|
| **Transaction** (`amlTransaction`) | `scored_transactions_stream` | `transaction_id` | `transaction_id` | `risk_band` → categorical; `laundering_probability` → number, 3 dp |
| **Transaction Risk Score** (`amlTransactionRiskScore`) | `transaction_risk_scores` | `score_id` | `score_id` | `model_version` categorical (one row per txn per model → challengers slot in here) |
| **Account** (`amlAccount`) | `accounts_summary` | `account_id` | `account_id` | `risk_tier` categorical; volumes as currency |
| **AML Alert** (`amlAlert`) | `alerts` | `alert_id` | `alert_id` | **edits enabled**; `status`, `priority`, `primary_typology`, `risk_band` categorical |
| **Investigation Case** (`amlInvestigationCase`) | `investigation_cases` | `case_id` | `title` | **edits enabled**; dataset is empty by design |
| **Laundering Pattern** (`amlLaunderingPattern`) | `laundering_patterns` | `transaction_id` | `pattern_id` | demo only |
| **Model Evaluation** (`amlModelEvaluation`) | `model_evaluation` | `metric` | `metric` | demo only |

Display-name map for Account: `volume_24h_inbound` → "24h Inbound Volume",
`volume_24h_outbound` → "24h Outbound Volume", `max_risk_score` → "Max Risk Score",
`high_risk_txn_count` → "High-risk Transactions".

## 2. Ontology Manager — links

All are **foreign-key links** (no join table). Create from the "many" side's property.

| Link API name | One | Many | FK property on the many side |
|---|---|---|---|
| `sent` | Account.account_id | Transaction | `from_account` |
| `received` | Account.account_id | Transaction | `to_account` |
| `hasScore` | Transaction.transaction_id | TransactionRiskScore | `transaction_id` |
| `concerns` | Transaction.transaction_id | Alert | `transaction_id` |
| `subject` | Account.account_id | Alert | `subject_account_id` |
| `counterparty` | Account.account_id | Alert | `counterparty_account_id` |
| `aggregates` | InvestigationCase.case_id | Alert | `case_id` |
| `groundTruth` | Transaction.transaction_id | LaunderingPattern | `transaction_id` (one-to-one) |

## 3. Ontology Manager — actions

| Action | Parameters | Rule | Submission criteria |
|---|---|---|---|
| **Triage Alert** | `alert` (Alert), `disposition` (Confirmed Suspicious / Needs Info), `note` (optional) | modify `alert`: `status = Triaged` | `alert.status == Open` |
| **Escalate to Case** | `alerts` (Alert list), `case_title` (text), `analyst_notes` (optional) | create InvestigationCase {`case_id` = uuid, `title`, `case_status = Open`, `sar_required = false`, `opened_ts = now`}; modify each alert {`status = Escalated`, `case_id` = new id} | at least one alert |
| **Close as False Positive** | `alert`, `reason` (text) | modify `alert`: `status = Closed` | `alert.status != Closed` |
| **Update Case** | `case`, `case_status`, `sar_required`, `analyst_notes` | modify `case` | — |

Turn on **action logging** for all four: that log is the regulator-facing audit trail.

## 4. Vertex — "Alert Network" graph

Create a Vertex graph template and save it (Workshop embeds it on the Alert Detail page).

- **Seed:** one Alert → expand `concerns` → Transaction → expand `sent` and `received` → the two
  Accounts.
- **Expansion rule (one click, "Show ±72h activity"):** from each Account, expand `sent` and
  `received` Transactions filtered to `timestamp` within ±72 h of the alert's `alerted_ts`
  (bind to a graph variable), **max 150 edges per account**, then one more hop of Accounts.
- **Styling:**
  - Transaction edge colour by `risk_band`: High = red, Medium = amber, Low = grey.
  - Edge width by `amount_usd` (log scale).
  - Account node colour by `risk_tier` (same palette); node size by `counterparty_count`.
  - Direction arrows on (money flow is the point).
- **Layout:** hierarchical left→right for fan patterns; switch to force-directed for cycles.
  Save both as presets "Flow" and "Cycle".
- Hide the ground-truth properties from node/edge tooltips.

## 5. Workshop — "AML Investigator Console"

Variables shared across pages: `selectedAlert`, `selectedAccount`, `selectedCase`, `showGroundTruth` (boolean, default false; the demo reveal switch).

### Page 1 — Alert Inbox
- KPI row (metric cards over Alert): Open alerts; P1 open; opened in last 24 h (`alerted_ts`);
  **High-band precision** = count(`is_laundering_ground_truth`=1 ∧ `risk_band`=High) / count(High)
  — show only when `showGroundTruth`.
- Filters: `status`, `priority`, `risk_band`, `primary_typology`, `alerted_ts` range,
  `subject_account_id` contains.
- Object table (Alert), default sort `laundering_probability` desc. Columns: `alert_id`, `priority`,
  `risk_band`, `laundering_probability`, `primary_typology`, `subject_account_id`,
  `counterparty_account_id`, `amount_usd`, `payment_format`, `alerted_ts`, `status`.
  Conditional formatting: P1 rows tinted.
- Row click → `selectedAlert` → navigate to Page 2. Multi-select → **Escalate to Case** button.
- Inline action buttons: Triage, Close as False Positive.

### Page 2 — Alert Detail & Network
- Left: Alert property card + linked Transaction card + linked TransactionRiskScore list
  (shows `model_version`, so champion vs challenger is visible).
- Centre: Vertex widget (template from §4) seeded on `selectedAlert`; buttons "Show ±72h activity",
  "Flow layout", "Cycle layout".
- Right: AIP widget (§6) with **Summarize network** and **Draft SAR narrative**.
- Footer: Triage · Escalate to Case · Close as False Positive.
- **Ground-truth reveal** (only when `showGroundTruth`): banner "True typology: {true_typology},
  pattern {pattern_id}" and the pattern's sibling transactions (LaunderingPattern filtered by
  `pattern_id`) highlighted in the graph.

### Page 3 — Account 360
- Header: `account_id`, `bank_id`, `risk_tier` badge, `max_risk_score`.
- Metric cards: 24h inbound, 24h outbound, in/out ratio, `counterparty_count`, `total_txn_count`,
  `high_risk_txn_count`, open alerts as subject.
- Chart: daily sum of `amount_usd` over `sent` ∪ `received` transactions, High-band txns as markers.
- Tabs: "Sent" table (link `sent`), "Received" table (link `received`), "Alerts" (links `subject`
  and `counterparty`).
- Mini Vertex seeded on the account (1 hop, ±7 days).

### Page 4 — Case Workbench
- Case list (InvestigationCase) + detail: aggregated Alerts table (link `aggregates`), combined
  Vertex seeded on all case alerts, `analyst_notes` editor and `sar_required` toggle (both through
  **Update Case**), `sar_draft` document panel filled by the AIP function, status buttons.

### Page 5 — Model & Evaluation (demo only)
- ModelEvaluation table (`metric`, `n`, `precision`, `recall`) and KPI cards for
  `precision_at_100` (0.91) and `band_High` precision (0.67).
- Bar chart: alerts by `primary_typology` vs `true_typology` (from Alert, filtered to ground
  truth = 1) — shows what the heuristic labels get right.
- Text block with the champion/challenger framing (model_version on every score).

## 6. AIP Logic — `draft_sar_narrative` and `summarize_network`

Both take an Alert (or Case) and traverse the ontology **before** the LLM block, so the model
only ever sees retrieved facts (prompt in `aip_sar_prompt.md`):

1. Alert → `concerns` Transaction → `hasScore` scores (all model versions).
2. Transaction → `sent`/`received` Accounts → their 24h volumes, risk tier, counterparty count.
3. Accounts → `sent`/`received` Transactions within ±72 h, capped at 200, summarised as
   counts, totals, distinct counterparties, and any cycle back to the subject.
4. Alert.`primary_typology` as the hypothesis to confirm or refute.

Output of `draft_sar_narrative` is written to `InvestigationCase.sar_draft` through **Update Case**,
never filed automatically. `summarize_network` returns text only.

## 7. Demo script (10 minutes)

1. Inbox sorted by probability: 269 P1 alerts. Pick the top one.
2. Alert Detail: network shows a fan-out of 10+ counterparties within 48 h; typology says Fan-Out.
3. Account 360 on the subject: 24h outbound volume dwarfs inbound; 1 prior alert.
4. Back on the alert: **Summarize network**, then **Escalate to Case** with two sibling alerts.
5. Case Workbench: **Draft SAR narrative**; edit a sentence; set `sar_required`.
6. Flip `showGroundTruth`: true typology Fan-Out, pattern HI-Small-P0xxx, all 12 member
   transactions light up — the model surfaced 9 of them.
7. Evaluation page: precision@100 = 0.91; High band precision = 0.67; every score carries a
   model version, so the next model is a challenger, not a replacement.
