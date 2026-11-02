/**
 * AML Investigation ontology — ontology-as-code (@osdk/maker).
 * Mirrors ontology/aml_ontology.yml v2; every property matches a column in the
 * backing datasets published to /AML_Compliance_Platform/03_Scored_Data.
 * Datasources of type "dataset" become Marketplace inputs bound at install time
 * (scored_transactions_stream, transaction_risk_scores, accounts_summary, alerts,
 * investigation_cases, laundering_patterns, model_evaluation).
 */
import {
  defineCreateObjectAction,
  defineLink,
  defineModifyObjectAction,
  defineObject,
} from "@osdk/maker";

const ds = [{ type: "dataset" as const }];

// ------------------------------------------------------------ object types
export const Transaction = defineObject({
  apiName: "amlTransaction",
  displayName: "Transaction",
  pluralDisplayName: "Transactions",
  primaryKeyPropertyApiName: "transactionId",
  titlePropertyApiName: "transactionId",
  description: "Scored transaction from the held-out stream (champion score denormalised).",
  icon: { locator: "exchange", color: "#2D72D2" },
  datasources: ds,
  properties: {
    transactionId: { type: "long", displayName: "Transaction ID" },
    timestamp: { type: "timestamp", displayName: "Timestamp" },
    fromAccount: { type: "string", displayName: "From Account" },
    toAccount: { type: "string", displayName: "To Account" },
    fromBank: { type: "string", displayName: "From Bank" },
    toBank: { type: "string", displayName: "To Bank" },
    amountUsd: { type: "double", displayName: "Amount (paid)" },
    amountReceived: { type: "double", displayName: "Amount Received" },
    paymentCurrency: { type: "string", displayName: "Payment Currency" },
    receivingCurrency: { type: "string", displayName: "Receiving Currency" },
    paymentFormat: { type: "string", displayName: "Payment Format" },
    launderingProbability: { type: "double", displayName: "Laundering Probability" },
    riskBand: { type: "string", displayName: "Risk Band" },
    isLaunderingGroundTruth: { type: "integer", displayName: "Ground Truth (demo only)" },
  },
});

export const TransactionRiskScore = defineObject({
  apiName: "amlTransactionRiskScore",
  displayName: "Transaction Risk Score",
  pluralDisplayName: "Transaction Risk Scores",
  primaryKeyPropertyApiName: "scoreId",
  titlePropertyApiName: "scoreId",
  description: "One row per transaction per model version (champion + challengers).",
  icon: { locator: "heat-grid", color: "#C87619" },
  datasources: ds,
  properties: {
    scoreId: { type: "string", displayName: "Score ID" },
    transactionId: { type: "long", displayName: "Transaction ID" },
    launderingProbability: { type: "double", displayName: "Laundering Probability" },
    riskBand: { type: "string", displayName: "Risk Band" },
    modelVersion: { type: "string", displayName: "Model Version" },
    scoredTs: { type: "timestamp", displayName: "Scored At" },
  },
});

export const Account = defineObject({
  apiName: "amlAccount",
  displayName: "Account",
  pluralDisplayName: "Accounts",
  primaryKeyPropertyApiName: "accountId",
  titlePropertyApiName: "accountId",
  description: "bank|account composite key with 24h volumes and max model risk.",
  icon: { locator: "bank-account", color: "#238C2C" },
  datasources: ds,
  properties: {
    accountId: { type: "string", displayName: "Account ID" },
    bankId: { type: "string", displayName: "Bank" },
    volume24hInbound: { type: "double", displayName: "24h Inbound Volume" },
    volume24hOutbound: { type: "double", displayName: "24h Outbound Volume" },
    totalTxnCount: { type: "integer", displayName: "Transactions" },
    counterpartyCount: { type: "integer", displayName: "Counterparties" },
    maxRiskScore: { type: "double", displayName: "Max Risk Score" },
    riskTier: { type: "string", displayName: "Risk Tier" },
    highRiskTxnCount: { type: "integer", displayName: "High-risk Transactions" },
    lastActiveTs: { type: "timestamp", displayName: "Last Active" },
  },
});

export const Alert = defineObject({
  apiName: "amlAlert",
  displayName: "AML Alert",
  pluralDisplayName: "AML Alerts",
  primaryKeyPropertyApiName: "alertId",
  titlePropertyApiName: "alertId",
  description: "High/Medium-band transactions queued for investigator triage.",
  icon: { locator: "warning-sign", color: "#CD4246" },
  editsEnabled: true,
  datasources: ds,
  properties: {
    alertId: { type: "string", displayName: "Alert ID" },
    transactionId: { type: "long", displayName: "Transaction ID" },
    subjectAccountId: { type: "string", displayName: "Subject Account" },
    counterpartyAccountId: { type: "string", displayName: "Counterparty Account" },
    status: { type: "string", displayName: "Status" },
    priority: { type: "string", displayName: "Priority" },
    primaryTypology: { type: "string", displayName: "Typology (derived)" },
    launderingProbability: { type: "double", displayName: "Laundering Probability" },
    riskBand: { type: "string", displayName: "Risk Band" },
    amountUsd: { type: "double", displayName: "Amount" },
    paymentFormat: { type: "string", displayName: "Payment Format" },
    alertedTs: { type: "timestamp", displayName: "Alerted At" },
    modelVersion: { type: "string", displayName: "Model Version" },
    caseId: { type: "string", displayName: "Case ID" },
    patternId: { type: "string", displayName: "Pattern ID (demo only)" },
    trueTypology: { type: "string", displayName: "True Typology (demo only)" },
    isLaunderingGroundTruth: { type: "integer", displayName: "Ground Truth (demo only)" },
  },
});

export const InvestigationCase = defineObject({
  apiName: "amlInvestigationCase",
  displayName: "Investigation Case",
  pluralDisplayName: "Investigation Cases",
  primaryKeyPropertyApiName: "caseId",
  titlePropertyApiName: "title",
  description: "Analyst-created case aggregating alerts; SAR draft is human-reviewed.",
  icon: { locator: "folder-open", color: "#7961DB" },
  editsEnabled: true,
  datasources: ds,
  properties: {
    caseId: { type: "string", displayName: "Case ID" },
    title: { type: "string", displayName: "Title" },
    analystNotes: { type: { type: "string", isLongText: true }, displayName: "Analyst Notes" },
    sarRequired: { type: "boolean", displayName: "SAR Required" },
    caseStatus: { type: "string", displayName: "Case Status" },
    openedTs: { type: "timestamp", displayName: "Opened At" },
    sarDraft: { type: { type: "string", isLongText: true }, displayName: "SAR Draft" },
  },
});

export const LaunderingPattern = defineObject({
  apiName: "amlLaunderingPattern",
  displayName: "Laundering Pattern (ground truth)",
  pluralDisplayName: "Laundering Patterns (ground truth)",
  primaryKeyPropertyApiName: "transactionId",
  titlePropertyApiName: "patternId",
  description: "Demo reveal layer from the AMLworld pattern file. Hide from triage views.",
  icon: { locator: "eye-open", color: "#5C7080" },
  datasources: ds,
  properties: {
    transactionId: { type: "long", displayName: "Transaction ID" },
    patternId: { type: "string", displayName: "Pattern ID" },
    trueTypology: { type: "string", displayName: "True Typology" },
  },
});

export const ModelEvaluation = defineObject({
  apiName: "amlModelEvaluation",
  displayName: "Model Evaluation",
  pluralDisplayName: "Model Evaluations",
  primaryKeyPropertyApiName: "metric",
  titlePropertyApiName: "metric",
  description: "Precision/recall per risk band and precision@K on the labeled test stream.",
  icon: { locator: "timeline-bar-chart", color: "#5C7080" },
  datasources: ds,
  properties: {
    metric: { type: "string", displayName: "Metric" },
    n: { type: "integer", displayName: "N" },
    precision: { type: "double", displayName: "Precision" },
    recall: { type: "double", displayName: "Recall" },
    modelVersion: { type: "string", displayName: "Model Version" },
    positives: { type: "integer", displayName: "Positives" },
    total: { type: "integer", displayName: "Total" },
  },
});

// ------------------------------------------------------------------ links
function oneToMany(
  apiName: string, one: any, oneSide: [string, string, string],
  many: any, manySide: [string, string, string], fk: string,
) {
  return defineLink({
    apiName,
    one: { object: one, metadata: { apiName: oneSide[0], displayName: oneSide[1], pluralDisplayName: oneSide[2], visibility: "NORMAL" } },
    toMany: { object: many, metadata: { apiName: manySide[0], displayName: manySide[1], pluralDisplayName: manySide[2], visibility: "NORMAL" } },
    manyForeignKeyProperty: fk,
  });
}

export const sent = oneToMany("amlSent", Account, ["sentTransactions", "Sent Transaction", "Sent Transactions"],
  Transaction, ["sender", "Sender", "Senders"], "fromAccount");
export const received = oneToMany("amlReceived", Account, ["receivedTransactions", "Received Transaction", "Received Transactions"],
  Transaction, ["receiver", "Receiver", "Receivers"], "toAccount");
export const hasScore = oneToMany("amlHasScore", Transaction, ["riskScores", "Risk Score", "Risk Scores"],
  TransactionRiskScore, ["transaction", "Transaction", "Transactions"], "transactionId");
export const concerns = oneToMany("amlConcerns", Transaction, ["alerts", "Alert", "Alerts"],
  Alert, ["transaction", "Transaction", "Transactions"], "transactionId");
export const subject = oneToMany("amlSubject", Account, ["subjectAlerts", "Alert as Subject", "Alerts as Subject"],
  Alert, ["subjectAccount", "Subject Account", "Subject Accounts"], "subjectAccountId");
export const counterparty = oneToMany("amlCounterparty", Account, ["counterpartyAlerts", "Alert as Counterparty", "Alerts as Counterparty"],
  Alert, ["counterpartyAccount", "Counterparty Account", "Counterparty Accounts"], "counterpartyAccountId");
export const aggregates = oneToMany("amlAggregates", InvestigationCase, ["alerts", "Alert", "Alerts"],
  Alert, ["investigationCase", "Investigation Case", "Investigation Cases"], "caseId");
export const groundTruth = oneToMany("amlGroundTruth", Transaction, ["groundTruth", "Ground Truth", "Ground Truth"],
  LaunderingPattern, ["transaction", "Transaction", "Transactions"], "transactionId");

// ---------------------------------------------------------------- actions
export const triageAlert = defineModifyObjectAction({
  objectType: Alert,
  apiName: "aml-triage-alert",
  displayName: "Triage Alert",
  description: "Mark an open alert as triaged.",
  excludedProperties: [
    "transactionId", "subjectAccountId", "counterpartyAccountId", "priority", "primaryTypology",
    "launderingProbability", "riskBand", "amountUsd", "paymentFormat", "alertedTs", "modelVersion",
    "caseId", "patternId", "trueTypology", "isLaunderingGroundTruth",
  ],
  parameterConfiguration: {
    status: { allowedValues: { type: "oneOf", oneOf: [{ label: "Triaged", value: { type: "string", string: "Triaged" } }] }, defaultValue: { type: "staticValue", staticValue: { type: "string", string: "Triaged" } } },
  },
});

export const closeFalsePositive = defineModifyObjectAction({
  objectType: Alert,
  apiName: "aml-close-false-positive",
  displayName: "Close as False Positive",
  description: "Close an alert; the disposition feeds model retraining.",
  excludedProperties: [
    "transactionId", "subjectAccountId", "counterpartyAccountId", "priority", "primaryTypology",
    "launderingProbability", "riskBand", "amountUsd", "paymentFormat", "alertedTs", "modelVersion",
    "caseId", "patternId", "trueTypology", "isLaunderingGroundTruth",
  ],
  parameterConfiguration: {
    status: { allowedValues: { type: "oneOf", oneOf: [{ label: "Closed", value: { type: "string", string: "Closed" } }] }, defaultValue: { type: "staticValue", staticValue: { type: "string", string: "Closed" } } },
  },
});

export const assignAlertToCase = defineModifyObjectAction({
  objectType: Alert,
  apiName: "aml-assign-alert-to-case",
  displayName: "Assign Alert to Case",
  description: "Escalate: set case_id and status = Escalated.",
  excludedProperties: [
    "transactionId", "subjectAccountId", "counterpartyAccountId", "priority", "primaryTypology",
    "launderingProbability", "riskBand", "amountUsd", "paymentFormat", "alertedTs", "modelVersion",
    "patternId", "trueTypology", "isLaunderingGroundTruth",
  ],
  parameterConfiguration: {
    status: { allowedValues: { type: "oneOf", oneOf: [{ label: "Escalated", value: { type: "string", string: "Escalated" } }] }, defaultValue: { type: "staticValue", staticValue: { type: "string", string: "Escalated" } } },
  },
});

export const openCase = defineCreateObjectAction({
  objectType: InvestigationCase,
  apiName: "aml-open-case",
  displayName: "Open Investigation Case",
  description: "Create a case; alerts are attached with Assign Alert to Case.",
  primaryKeyOption: "autoGenerated",
  excludedProperties: ["sarDraft"],
  parameterConfiguration: {
    caseStatus: { allowedValues: { type: "oneOf", oneOf: [
      { label: "Open", value: { type: "string", string: "Open" } },
      { label: "In Review", value: { type: "string", string: "In Review" } },
      { label: "SAR Filed", value: { type: "string", string: "SAR Filed" } },
      { label: "Closed", value: { type: "string", string: "Closed" } },
    ] }, defaultValue: { type: "staticValue", staticValue: { type: "string", string: "Open" } } },
  },
});

export const updateCase = defineModifyObjectAction({
  objectType: InvestigationCase,
  apiName: "aml-update-case",
  displayName: "Update Case",
  description: "Edit notes, SAR flag, status, and the reviewed SAR draft.",
  excludedProperties: ["title", "openedTs"],
  parameterConfiguration: {
    caseStatus: { allowedValues: { type: "oneOf", oneOf: [
      { label: "Open", value: { type: "string", string: "Open" } },
      { label: "In Review", value: { type: "string", string: "In Review" } },
      { label: "SAR Filed", value: { type: "string", string: "SAR Filed" } },
      { label: "Closed", value: { type: "string", string: "Closed" } },
    ] } },
  },
});
