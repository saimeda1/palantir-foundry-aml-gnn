
import { wrapWithProxy, OntologyEntityTypeEnum } from '@osdk/maker';
import type { ObjectType } from '@osdk/maker';

/** @type {import('@osdk/maker').ObjectType} */
const amlInvestigationCase_base: ObjectType = {
  "apiName": "aml.amlInvestigationCase",
  "displayName": "Investigation Case",
  "pluralDisplayName": "Investigation Cases",
  "primaryKeyPropertyApiName": "caseId",
  "titlePropertyApiName": "title",
  "description": "Analyst-created case aggregating alerts; SAR draft is human-reviewed.",
  "icon": {
    "locator": "folder-open",
    "color": "#7961DB"
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
      "displayName": "Case ID",
      "apiName": "caseId"
    },
    {
      "type": "string",
      "displayName": "Title",
      "apiName": "title"
    },
    {
      "type": {
        "type": "string",
        "isLongText": true
      },
      "displayName": "Analyst Notes",
      "apiName": "analystNotes"
    },
    {
      "type": "boolean",
      "displayName": "SAR Required",
      "apiName": "sarRequired"
    },
    {
      "type": "string",
      "displayName": "Case Status",
      "apiName": "caseStatus"
    },
    {
      "type": "timestamp",
      "displayName": "Opened At",
      "apiName": "openedTs"
    },
    {
      "type": {
        "type": "string",
        "isLongText": true
      },
      "displayName": "SAR Draft",
      "apiName": "sarDraft"
    }
  ],
  "__type": OntologyEntityTypeEnum.OBJECT_TYPE
} as unknown as ObjectType;
        
export const amlInvestigationCase: ObjectType = wrapWithProxy(amlInvestigationCase_base);
        