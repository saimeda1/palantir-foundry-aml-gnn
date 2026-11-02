
import { wrapWithProxy, OntologyEntityTypeEnum } from '@osdk/maker';
import type { LinkType } from '@osdk/maker';

/** @type {import('@osdk/maker').LinkType} */
const amlHasScore_base: LinkType = {
  "apiName": "amlHasScore",
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
      "apiName": "riskScores",
      "displayMetadata": {
        "displayName": "Risk Score",
        "pluralDisplayName": "Risk Scores",
        "visibility": "NORMAL",
        "groupDisplayName": ""
      },
      "typeClasses": []
    }
  },
  "toMany": {
    "object": {
      "apiName": "aml.amlTransactionRiskScore",
      "displayName": "Transaction Risk Score",
      "pluralDisplayName": "Transaction Risk Scores",
      "primaryKeyPropertyApiName": "scoreId",
      "titlePropertyApiName": "scoreId",
      "description": "One row per transaction per model version (champion + challengers).",
      "icon": {
        "locator": "heat-grid",
        "color": "#C87619"
      },
      "datasources": [
        {
          "type": "dataset"
        }
      ],
      "properties": {
        "scoreId": {
          "type": "string",
          "displayName": "Score ID"
        },
        "transactionId": {
          "type": "long",
          "displayName": "Transaction ID"
        },
        "launderingProbability": {
          "type": "double",
          "displayName": "Laundering Probability"
        },
        "riskBand": {
          "type": "string",
          "displayName": "Risk Band"
        },
        "modelVersion": {
          "type": "string",
          "displayName": "Model Version"
        },
        "scoredTs": {
          "type": "timestamp",
          "displayName": "Scored At"
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
        
export const amlHasScore: LinkType = wrapWithProxy(amlHasScore_base);
        