
import { wrapWithProxy, OntologyEntityTypeEnum } from '@osdk/maker';
import type { LinkType } from '@osdk/maker';

/** @type {import('@osdk/maker').LinkType} */
const amlConcerns_base: LinkType = {
  "apiName": "amlConcerns",
  "one": {
    "object": {
      "apiName": "aml.amlTransaction",
      "displayName": "Transaction",
      "pluralDisplayName": "Transactions",
      "primaryKeyPropertyApiName": "transactionId",
      "titlePropertyApiName": "transactionId",
      "description": "Scored transaction from the held-out stream (champion score denormalised).",
      "icon": {
        "locator": "exchange",
        "color": "#2D72D2"
      },
      "datasources": [
        {
          "type": "dataset"
        }
      ],
      "properties": {
        "transactionId": {
          "type": "long",
          "displayName": "Transaction ID"
        },
        "timestamp": {
          "type": "timestamp",
          "displayName": "Timestamp"
        },
        "fromAccount": {
          "type": "string",
          "displayName": "From Account"
        },
        "toAccount": {
          "type": "string",
          "displayName": "To Account"
        },
        "fromBank": {
          "type": "string",
          "displayName": "From Bank"
        },
        "toBank": {
          "type": "string",
          "displayName": "To Bank"
        },
        "amountUsd": {
          "type": "double",
          "displayName": "Amount (paid)"
        },
        "amountReceived": {
          "type": "double",
          "displayName": "Amount Received"
        },
        "paymentCurrency": {
          "type": "string",
          "displayName": "Payment Currency"
        },
        "receivingCurrency": {
          "type": "string",
          "displayName": "Receiving Currency"
        },
        "paymentFormat": {
          "type": "string",
          "displayName": "Payment Format"
        },
        "launderingProbability": {
          "type": "double",
          "displayName": "Laundering Probability"
        },
        "riskBand": {
          "type": "string",
          "displayName": "Risk Band"
        },
        "isLaunderingGroundTruth": {
          "type": "integer",
          "displayName": "Ground Truth (demo only)"
        }
      }
    },
    "metadata": {
      "apiName": "alerts",
      "displayMetadata": {
        "displayName": "Alert",
        "pluralDisplayName": "Alerts",
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
      "apiName": "transaction",
      "displayMetadata": {
        "displayName": "Transaction",
        "pluralDisplayName": "Transactions",
        "visibility": "NORMAL",
        "groupDisplayName": ""
      },
      "typeClasses": []
    }
  },
  "manyForeignKeyProperty": "transactionId",
  "__type": OntologyEntityTypeEnum.LINK_TYPE
} as unknown as LinkType;
        
export const amlConcerns: LinkType = wrapWithProxy(amlConcerns_base);
        