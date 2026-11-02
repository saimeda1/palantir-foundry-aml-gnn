
import { wrapWithProxy, OntologyEntityTypeEnum } from '@osdk/maker';
import type { ObjectType } from '@osdk/maker';

/** @type {import('@osdk/maker').ObjectType} */
const amlAlert_base: ObjectType = {
  "apiName": "aml.amlAlert",
  "displayName": "AML Alert",
  "pluralDisplayName": "AML Alerts",
  "primaryKeyPropertyApiName": "alertId",
  "titlePropertyApiName": "alertId",
  "description": "High/Medium-band transactions queued for investigator triage.",
  "icon": {
    "locator": "warning-sign",
    "color": "#CD4246"
  },
  "editsEnabled": true,
  "datasources": [
    {
      "type": "dataset"
    }
  ],
  "properties": [
    {
      "type": "string",
      "displayName": "Alert ID",
      "apiName": "alertId"
    },
    {
      "type": "long",
      "displayName": "Transaction ID",
      "apiName": "transactionId"
    },
    {
      "type": "string",
      "displayName": "Subject Account",
      "apiName": "subjectAccountId"
    },
    {
      "type": "string",
      "displayName": "Counterparty Account",
      "apiName": "counterpartyAccountId"
    },
    {
      "type": "string",
      "displayName": "Status",
      "apiName": "status"
    },
    {
      "type": "string",
      "displayName": "Priority",
      "apiName": "priority"
    },
    {
      "type": "string",
      "displayName": "Typology (derived)",
      "apiName": "primaryTypology"
    },
    {
      "type": "double",
      "displayName": "Laundering Probability",
      "apiName": "launderingProbability"
    },
    {
      "type": "string",
      "displayName": "Risk Band",
      "apiName": "riskBand"
    },
    {
      "type": "double",
      "displayName": "Amount",
      "apiName": "amountUsd"
    },
    {
      "type": "string",
      "displayName": "Payment Format",
      "apiName": "paymentFormat"
    },
    {
      "type": "timestamp",
      "displayName": "Alerted At",
      "apiName": "alertedTs"
    },
    {
      "type": "string",
      "displayName": "Model Version",
      "apiName": "modelVersion"
    },
    {
      "type": "string",
      "displayName": "Case ID",
      "apiName": "caseId"
    },
    {
      "type": "string",
      "displayName": "Pattern ID (demo only)",
      "apiName": "patternId"
    },
    {
      "type": "string",
      "displayName": "True Typology (demo only)",
      "apiName": "trueTypology"
    },
    {
      "type": "integer",
      "displayName": "Ground Truth (demo only)",
      "apiName": "isLaunderingGroundTruth"
    }
  ],
  "__type": OntologyEntityTypeEnum.OBJECT_TYPE
} as unknown as ObjectType;
        
export const amlAlert: ObjectType = wrapWithProxy(amlAlert_base);
        