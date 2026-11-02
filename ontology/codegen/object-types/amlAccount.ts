
import { wrapWithProxy, OntologyEntityTypeEnum } from '@osdk/maker';
import type { ObjectType } from '@osdk/maker';

/** @type {import('@osdk/maker').ObjectType} */
const amlAccount_base: ObjectType = {
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
  "properties": [
    {
      "type": "string",
      "displayName": "Account ID",
      "apiName": "accountId"
    },
    {
      "type": "string",
      "displayName": "Bank",
      "apiName": "bankId"
    },
    {
      "type": "double",
      "displayName": "24h Inbound Volume",
      "apiName": "volume24hInbound"
    },
    {
      "type": "double",
      "displayName": "24h Outbound Volume",
      "apiName": "volume24hOutbound"
    },
    {
      "type": "integer",
      "displayName": "Transactions",
      "apiName": "totalTxnCount"
    },
    {
      "type": "integer",
      "displayName": "Counterparties",
      "apiName": "counterpartyCount"
    },
    {
      "type": "double",
      "displayName": "Max Risk Score",
      "apiName": "maxRiskScore"
    },
    {
      "type": "string",
      "displayName": "Risk Tier",
      "apiName": "riskTier"
    },
    {
      "type": "integer",
      "displayName": "High-risk Transactions",
      "apiName": "highRiskTxnCount"
    },
    {
      "type": "timestamp",
      "displayName": "Last Active",
      "apiName": "lastActiveTs"
    }
  ],
  "__type": OntologyEntityTypeEnum.OBJECT_TYPE
} as unknown as ObjectType;
        
export const amlAccount: ObjectType = wrapWithProxy(amlAccount_base);
        