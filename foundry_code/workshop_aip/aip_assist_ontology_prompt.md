# Prompt for AIP Assist — build the AML Investigator ontology

Paste everything below the line into AIP Assist (open it from the Ontology Manager page so it has
ontology context). If Assist can only advise rather than create, it will hand back the same steps
in order; follow them in Ontology Manager. Dataset RIDs are real; column names are exact.

---

I need you to build an ontology for an AML (anti-money-laundering) investigation workflow in
Ontology Manager, in the default ontology of this enrollment. All backing datasets already exist,
with schemas, in the project folder `/AML_Compliance_Platform/03_Scored_Data`. Column names below
are exact (camelCase). Use the API-name prefix `aml` for everything. Create the object types first,
then the links, then the actions, saving and applying after each step. Tell me before each step
what you are about to create, and after each step what was created.

## 1. Object types (7) — each created from its dataset

| Display name | API name | Backing dataset (name / RID) | Primary key | Title property |
|---|---|---|---|---|
| Transaction | amlTransaction | scored_transactions_stream / ri.foundry.main.dataset.77edf771-f067-48bf-947f-43f5189fa776 | transactionId | transactionId |
| Transaction Risk Score | amlTransactionRiskScore | transaction_risk_scores / ri.foundry.main.dataset.b83aab09-9d6c-45c0-a679-05f198e8106c | scoreId | scoreId |
| Account | amlAccount | accounts_summary / ri.foundry.main.dataset.c808a42f-96b0-432a-a584-d0bfe44b3cc5 | accountId | accountId |
| AML Alert | amlAlert | alerts / ri.foundry.main.dataset.6e29110d-b2b8-4033-8aef-2c98f10f047f | alertId | alertId |
| Investigation Case | amlInvestigationCase | investigation_cases / ri.foundry.main.dataset.15163afd-d20d-4bf2-995f-05abc44d3e98 | caseId | title |
| Laundering Pattern | amlLaunderingPattern | laundering_patterns / ri.foundry.main.dataset.744f4737-a16a-49e2-bc15-cf8789621e64 | transactionId | patternId |
| Model Evaluation | amlModelEvaluation | model_evaluation / ri.foundry.main.dataset.2144c316-fef1-4435-85b6-6c78a59f7818 | metric | metric |

Map every dataset column to a property with the same API name as the column. Columns per dataset:

- scored_transactions_stream: transactionId (long), timestamp (timestamp), fromAccount, toAccount,
  fromBank, toBank (string), amountUsd, amountReceived (double), paymentCurrency,
  receivingCurrency, paymentFormat (string), launderingProbability (double), riskBand (string),
  isLaunderingGroundTruth (integer).
- transaction_risk_scores: scoreId (string), transactionId (long), launderingProbability (double),
  riskBand (string), modelVersion (string), scoredTs (timestamp).
- accounts_summary: accountId, bankId (string), volume24hInbound, volume24hOutbound (double),
  totalTxnCount, counterpartyCount (integer), maxRiskScore (double), riskTier (string),
  highRiskTxnCount (integer), lastActiveTs (timestamp).
- alerts: alertId (string), transactionId (long), subjectAccountId, counterpartyAccountId, status,
  priority, primaryTypology (string), launderingProbability (double), riskBand (string),
  amountUsd (double), paymentFormat (string), alertedTs (timestamp), modelVersion, caseId,
  patternId, trueTypology (string), isLaunderingGroundTruth (integer).
- investigation_cases: caseId, title, analystNotes (string), sarRequired (boolean),
  caseStatus (string), openedTs (timestamp), sarDraft (string). The dataset is empty on purpose;
  rows are created by the Open Case action.
- laundering_patterns: transactionId (long), patternId, trueTypology (string).
- model_evaluation: metric (string), n (integer), precision, recall (double), modelVersion
  (string), positives, total (integer).

Settings:
- Enable **edits** (user-editable, writeback) on AML Alert and Investigation Case. The other five
  are read-only.
- Display names: volume24hInbound → "24h Inbound Volume", volume24hOutbound → "24h Outbound
  Volume", maxRiskScore → "Max Risk Score", highRiskTxnCount → "High-risk Transactions",
  launderingProbability → "Laundering Probability", riskBand → "Risk Band",
  primaryTypology → "Typology (derived)".
- Mark riskBand, riskTier, status, priority, primaryTypology, caseStatus, paymentFormat as
  categorical where the type supports it. Values: riskBand/riskTier = Low, Medium, High;
  status = Open, Triaged, Escalated, Closed; priority = P1, P2, P3; caseStatus = Open, In Review,
  SAR Filed, Closed.
- Mark these as hidden/not shown in default views (ground truth for the demo reveal):
  amlTransaction.isLaunderingGroundTruth, amlAlert.patternId, amlAlert.trueTypology,
  amlAlert.isLaunderingGroundTruth.

## 2. Links (8) — all foreign-key links, created from the "many" side's property

| API name | One side (object.property) | Many side (object.foreign-key property) | Cardinality |
|---|---|---|---|
| amlSent | amlAccount.accountId | amlTransaction.fromAccount | one-to-many |
| amlReceived | amlAccount.accountId | amlTransaction.toAccount | one-to-many |
| amlHasScore | amlTransaction.transactionId | amlTransactionRiskScore.transactionId | one-to-many |
| amlConcerns | amlTransaction.transactionId | amlAlert.transactionId | one-to-many |
| amlSubject | amlAccount.accountId | amlAlert.subjectAccountId | one-to-many |
| amlCounterparty | amlAccount.accountId | amlAlert.counterpartyAccountId | one-to-many |
| amlAggregates | amlInvestigationCase.caseId | amlAlert.caseId | one-to-many |
| amlGroundTruth | amlTransaction.transactionId | amlLaunderingPattern.transactionId | one-to-one |

Display names: sent, received, has score, concerns, subject, counterparty, aggregates, ground truth.

## 3. Actions (5) — enable action logging on every one

1. **Triage Alert** (`aml-triage-alert`): parameters alert (AML Alert), disposition (string,
   allowed: Confirmed Suspicious, Needs Info), note (string, optional). Rule: modify alert, set
   status = "Triaged". Submission criterion: alert.status == "Open".
2. **Close as False Positive** (`aml-close-false-positive`): parameters alert (AML Alert), reason
   (string, required). Rule: modify alert, set status = "Closed". Criterion: alert.status != "Closed".
3. **Open Case** (`aml-open-case`): parameters title (string), analystNotes (string, optional).
   Rule: create Investigation Case with caseId = generated UUID, title = title,
   analystNotes = analystNotes, caseStatus = "Open", sarRequired = false, openedTs = now.
4. **Assign Alert to Case** (`aml-assign-alert-to-case`): parameters alert (AML Alert), case
   (Investigation Case). Rule: modify alert, set caseId = case.caseId and status = "Escalated".
5. **Update Case** (`aml-update-case`): parameters case (Investigation Case), caseStatus (string,
   allowed: Open, In Review, SAR Filed, Closed), sarRequired (boolean), analystNotes (string,
   optional), sarDraft (string, optional). Rule: modify case with the given values.

## 4. Verify

After applying, confirm in Object Explorer that AML Alert returns about 2,400 objects, that the
top alert by launderingProbability links to exactly one Transaction and two Accounts, and that
Account "sent" and "received" links return transactions. Report anything that failed to index.
