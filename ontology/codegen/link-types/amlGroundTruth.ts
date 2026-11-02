
import { wrapWithProxy, OntologyEntityTypeEnum } from '@osdk/maker';
import type { LinkType } from '@osdk/maker';

/** @type {import('@osdk/maker').LinkType} */
const amlGroundTruth_base: LinkType = {
  "apiName": "amlGroundTruth",
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
      "apiName": "groundTruth",
      "displayMetadata": {
        "displayName": "Ground Truth",
        "pluralDisplayName": "Ground Truth",
        "visibility": "NORMAL",
        "groupDisplayName": ""
      },
      "typeClasses": []
    }
  },
  "toMany": {
    "object": {
      "apiName": "aml.amlLaunderingPattern",
      "displayName": "Laundering Pattern (ground truth)",
      "pluralDisplayName": "Laundering Patterns (ground truth)",
      "primaryKeyPropertyApiName": "transactionId",
      "titlePropertyApiName": "patternId",
      "description": "Demo reveal layer from the AMLworld pattern file. Hide from triage views.",
      "icon": {
        "locator": "eye-open",
        "color": "#5C7080"
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
        "patternId": {
          "type": "string",
          "displayName": "Pattern ID"
        },
        "trueTypology": {
          "type": "string",
          "displayName": "True Typology"
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
        
export const amlGroundTruth: LinkType = wrapWithProxy(amlGroundTruth_base);
        