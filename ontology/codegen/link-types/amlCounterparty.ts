
import { wrapWithProxy, OntologyEntityTypeEnum } from '@osdk/maker';
import type { LinkType } from '@osdk/maker';

/** @type {import('@osdk/maker').LinkType} */
const amlCounterparty_base: LinkType = {
  "apiName": "amlCounterparty",
  "one": {
    "object": {
      "apiName": "aml.amlAccount",
      "displayName": "Account",
      "pluralDisplayName": "Accounts",
      "primaryKeyPropertyApiName": "accountId",
      "titlePropertyApiName": "accountId",
      "description": "bank|account composite key with 24h volumes and max model risk.",
      "icon": {
        "locator": "bank-account",
        "color": "#238C2C"
      },
      "datasources": [
        {
          "type": "dataset"
        }
      ],
      "properties": {
        "accountId": {
          "type": "string",
          "displayName": "Account ID"
        },
        "bankId": {
          "type": "string",
          "displayName": "Bank"
        },
        "volume24hInbound": {
          "type": "double",
          "displayName": "24h Inbound Volume"
        },
        "volume24hOutbound": {
          "type": "double",
          "displayName": "24h Outbound Volume"
        },
        "totalTxnCount": {
          "type": "integer",
          "displayName": "Transactions"
        },
        "counterpartyCount": {
          "type": "integer",
          "displayName": "Counterparties"
        },
        "maxRiskScore": {
          "type": "double",
          "displayName": "Max Risk Score"
        },
        "riskTier": {
          "type": "string",
          "displayName": "Risk Tier"
        },
        "highRiskTxnCount": {
          "type": "integer",
          "displayName": "High-risk Transactions"
        },
        "lastActiveTs": {
          "type": "timestamp",
          "displayName": "Last Active"
        }
      }
    },
    "metadata": {
      "apiName": "counterpartyAlerts",
      "displayMetadata": {
        "displayName": "Alert as Counterparty",
        "pluralDisplayName": "Alerts as Counterparty",
        "visibility": "NORMAL",
        "groupDisplayName": ""
      },
      "typeClasses": []
    }
  },
  "toMany": {
    "object": {
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
      "properties": {
        "alertId": {
          "type": "string",
          "displayName": "Alert ID"
        },
        "transactionId": {
          "type": "long",
          "displayName": "Transaction ID"
        },
        "subjectAccountId": {
          "type": "string",
          "displayName": "Subject Account"
        },
        "counterpartyAccountId": {
          "type": "string",
          "displayName": "Counterparty Account"
        },
        "status": {
          "type": "string",
          "displayName": "Status"
        },
        "priority": {
          "type": "string",
          "displayName": "Priority"
        },
        "primaryTypology": {
          "type": "string",
          "displayName": "Typology (derived)"
        },
        "launderingProbability": {
          "type": "double",
          "displayName": "Laundering Probability"
        },
        "riskBand": {
          "type": "string",
          "displayName": "Risk Band"
        },
        "amountUsd": {
          "type": "double",
          "displayName": "Amount"
        },
        "paymentFormat": {
          "type": "string",
          "displayName": "Payment Format"
        },
        "alertedTs": {
          "type": "timestamp",
          "displayName": "Alerted At"
        },
        "modelVersion": {
          "type": "string",
          "displayName": "Model Version"
        },
        "caseId": {
          "type": "string",
          "displayName": "Case ID"
        },
        "patternId": {
          "type": "string",
          "displayName": "Pattern ID (demo only)"
        },
        "trueTypology": {
          "type": "string",
          "displayName": "True Typology (demo only)"
        },
        "isLaunderingGroundTruth": {
          "type": "integer",
          "displayName": "Ground Truth (demo only)"
        }
      }
    },
    "metadata": {
      "apiName": "counterpartyAccount",
      "displayMetadata": {
        "displayName": "Counterparty Account",
        "pluralDisplayName": "Counterparty Accounts",
        "visibility": "NORMAL",
        "groupDisplayName": ""
      },
      "typeClasses": []
    }
  },
  "manyForeignKeyProperty": "counterpartyAccountId",
  "__type": OntologyEntityTypeEnum.LINK_TYPE
} as unknown as LinkType;
        
export const amlCounterparty: LinkType = wrapWithProxy(amlCounterparty_base);
        