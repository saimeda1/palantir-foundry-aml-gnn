
import { wrapWithProxy, OntologyEntityTypeEnum } from '@osdk/maker';
import type { ActionType } from '@osdk/maker';

/** @type {import('@osdk/maker').ActionType} */
const amlOpenCase_base: ActionType = {
  "apiName": "aml.aml-open-case",
  "displayName": "Open Investigation Case",
  "description": "Create a case; alerts are attached with Assign Alert to Case.",
  "parameters": [
    {
      "id": "caseId",
      "displayName": "Case ID",
      "type": "string",
      "validation": {
        "required": false,
        "allowedValues": {
          "type": "text"
        }
      }
    },
    {
      "id": "title",
      "displayName": "Title",
      "type": "string",
      "validation": {
        "required": false,
        "allowedValues": {
          "type": "text"
        }
      }
    },
    {
      "id": "analystNotes",
      "displayName": "Analyst Notes",
      "type": "string",
      "validation": {
        "required": false,
        "allowedValues": {
          "type": "text"
        }
      }
    },
    {
      "id": "sarRequired",
      "displayName": "SAR Required",
      "type": "boolean",
      "validation": {
        "required": false,
        "allowedValues": {
          "type": "boolean"
        }
      }
    },
    {
      "id": "caseStatus",
      "displayName": "Case Status",
      "type": "string",
      "validation": {
        "allowedValues": {
          "type": "oneOf",
          "oneOf": [
            {
              "label": "Open",
              "value": {
                "type": "string",
                "string": "Open"
              }
            },
            {
              "label": "In Review",
              "value": {
                "type": "string",
                "string": "In Review"
              }
            },
            {
              "label": "SAR Filed",
              "value": {
                "type": "string",
                "string": "SAR Filed"
              }
            },
            {
              "label": "Closed",
              "value": {
                "type": "string",
                "string": "Closed"
              }
            }
          ]
        },
        "defaultValue": {
          "type": "staticValue",
          "staticValue": {
            "type": "string",
            "string": "Open"
          }
        },
        "required": false
      },
      "defaultValue": {
        "type": "staticValue",
        "staticValue": {
          "type": "string",
          "string": "Open"
        }
      }
    },
    {
      "id": "openedTs",
      "displayName": "Opened At",
      "type": "timestamp",
      "validation": {
        "required": false,
        "allowedValues": {
          "type": "datetime"
        }
      }
    }
  ],
  "status": "active",
  "entities": {
    "affectedInterfaceTypes": [],
    "affectedObjectTypes": [
      "aml.amlInvestigationCase"
    ],
    "affectedLinkTypes": [],
    "typeGroups": []
  },
  "rules": [
    {
      "type": "addObjectRule",
      "addObjectRule": {
        "objectTypeId": "aml.amlInvestigationCase",
        "propertyValues": {
          "caseId": {
            "type": "parameterId",
            "parameterId": "caseId"
          },
          "title": {
            "type": "parameterId",
            "parameterId": "title"
          },
          "analystNotes": {
            "type": "parameterId",
            "parameterId": "analystNotes"
          },
          "sarRequired": {
            "type": "parameterId",
            "parameterId": "sarRequired"
          },
          "caseStatus": {
            "type": "parameterId",
            "parameterId": "caseStatus"
          },
          "openedTs": {
            "type": "parameterId",
            "parameterId": "openedTs"
          }
        },
        "structFieldValues": {}
      }
    }
  ],
  "parameterOrdering": [
    "caseStatus",
    "caseId",
    "title",
    "analystNotes",
    "sarRequired",
    "openedTs"
  ],
  "__type": OntologyEntityTypeEnum.ACTION_TYPE
} as unknown as ActionType;
        
export const amlOpenCase: ActionType = wrapWithProxy(amlOpenCase_base);
        