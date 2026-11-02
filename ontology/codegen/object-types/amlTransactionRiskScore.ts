
import { wrapWithProxy, OntologyEntityTypeEnum } from '@osdk/maker';
import type { ObjectType } from '@osdk/maker';

/** @type {import('@osdk/maker').ObjectType} */
const amlTransactionRiskScore_base: ObjectType = {
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
  "properties": [
    {
      "type": "string",
      "displayName": "Score ID",
      "apiName": "scoreId"
    },
    {
      "type": "long",
      "displayName": "Transaction ID",
      "apiName": "transactionId"
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
      "type": "string",
      "displayName": "Model Version",
      "apiName": "modelVersion"
    },
    {
      "type": "timestamp",
      "displayName": "Scored At",
      "apiName": "scoredTs"
    }
  ],
  "__type": OntologyEntityTypeEnum.OBJECT_TYPE
} as unknown as ObjectType;
        
export const amlTransactionRiskScore: ObjectType = wrapWithProxy(amlTransactionRiskScore_base);
        