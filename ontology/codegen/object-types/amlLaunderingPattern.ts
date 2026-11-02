
import { wrapWithProxy, OntologyEntityTypeEnum } from '@osdk/maker';
import type { ObjectType } from '@osdk/maker';

/** @type {import('@osdk/maker').ObjectType} */
const amlLaunderingPattern_base: ObjectType = {
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
  "properties": [
    {
      "type": "long",
      "displayName": "Transaction ID",
      "apiName": "transactionId"
    },
    {
      "type": "string",
      "displayName": "Pattern ID",
      "apiName": "patternId"
    },
    {
      "type": "string",
      "displayName": "True Typology",
      "apiName": "trueTypology"
    }
  ],
  "__type": OntologyEntityTypeEnum.OBJECT_TYPE
} as unknown as ObjectType;
        
export const amlLaunderingPattern: ObjectType = wrapWithProxy(amlLaunderingPattern_base);
        