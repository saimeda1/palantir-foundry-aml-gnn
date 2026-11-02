
import { wrapWithProxy, OntologyEntityTypeEnum } from '@osdk/maker';
import type { ObjectType } from '@osdk/maker';

/** @type {import('@osdk/maker').ObjectType} */
const amlTransaction_base: ObjectType = {
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
  "properties": [
    {
      "type": "long",
      "displayName": "Transaction ID",
      "apiName": "transactionId"
    },
    {
      "type": "timestamp",
      "displayName": "Timestamp",
      "apiName": "timestamp"
    },
    {
      "type": "string",
      "displayName": "From Account",
      "apiName": "fromAccount"
    },
    {
      "type": "string",
      "displayName": "To Account",
      "apiName": "toAccount"
    },
    {
      "type": "string",
      "displayName": "From Bank",
      "apiName": "fromBank"
    },
    {
      "type": "string",
      "displayName": "To Bank",
      "apiName": "toBank"
    },
    {
      "type": "double",
      "displayName": "Amount (paid)",
      "apiName": "amountUsd"
    },
    {
      "type": "double",
      "displayName": "Amount Received",
      "apiName": "amountReceived"
    },
    {
      "type": "string",
      "displayName": "Payment Currency",
      "apiName": "paymentCurrency"
    },
    {
      "type": "string",
      "displayName": "Receiving Currency",
      "apiName": "receivingCurrency"
    },
    {
      "type": "string",
      "displayName": "Payment Format",
      "apiName": "paymentFormat"
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
      "type": "integer",
      "displayName": "Ground Truth (demo only)",
      "apiName": "isLaunderingGroundTruth"
    }
  ],
  "__type": OntologyEntityTypeEnum.OBJECT_TYPE
} as unknown as ObjectType;
        
export const amlTransaction: ObjectType = wrapWithProxy(amlTransaction_base);
        