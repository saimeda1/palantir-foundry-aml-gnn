
import { wrapWithProxy, OntologyEntityTypeEnum } from '@osdk/maker';
import type { LinkType } from '@osdk/maker';

/** @type {import('@osdk/maker').LinkType} */
const amlSent_base: LinkType = {
  "apiName": "amlSent",
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
      "apiName": "sentTransactions",
      "displayMetadata": {
        "displayName": "Sent Transaction",
        "pluralDisplayName": "Sent Transactions",
        "visibility": "NORMAL",
        "groupDisplayName": ""
      },
      "typeClasses": []
    }
  },
  "toMany": {
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
      "apiName": "sender",
      "displayMetadata": {
        "displayName": "Sender",
        "pluralDisplayName": "Senders",
        "visibility": "NORMAL",
        "groupDisplayName": ""
      },
      "typeClasses": []
    }
  },
  "manyForeignKeyProperty": "fromAccount",
  "__type": OntologyEntityTypeEnum.LINK_TYPE
} as unknown as LinkType;
        
export const amlSent: LinkType = wrapWithProxy(amlSent_base);
        