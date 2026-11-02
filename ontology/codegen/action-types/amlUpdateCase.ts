
import { wrapWithProxy, OntologyEntityTypeEnum } from '@osdk/maker';
import type { ActionType } from '@osdk/maker';

/** @type {import('@osdk/maker').ActionType} */
const amlUpdateCase_base: ActionType = {
  "apiName": "aml.aml-update-case",
  "displayName": "Update Case",
  "description": "Edit notes, SAR flag, status, and the reviewed SAR draft.",
  "parameters": [
    {
      "id": "objectToModifyParameter",
      "displayName": "Modify object",
      "type": {
        "type": "objectReference",
        "objectReference": {
          "objectTypeId": "aml.amlInvestigationCase"
        }
      },
      "validation": {
        "allowedValues": {
          "type": "objectQuery"
        },
        "required": true
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
      },
      "defaultValue": {
        "type": "objectParameterPropertyValue",
        "objectParameterPropertyValue": {
          "parameterId": "objectToModifyParameter",
          "propertyTypeId": "analystNotes"
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
      },
      "defaultValue": {
        "type": "objectParameterPropertyValue",
        "objectParameterPropertyValue": {
          "parameterId": "objectToModifyParameter",
          "propertyTypeId": "sarRequired"
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
        "required": false
      },
      "defaultValue": {
        "type": "objectParameterPropertyValue",
        "objectParameterPropertyValue": {
          "parameterId": "objectToModifyParameter",
          "propertyTypeId": "caseStatus"
        }
      }
    },
    {
      "id": "sarDraft",
      "displayName": "SAR Draft",
      "type": "string",
      "validation": {
        "required": false,
        "allowedValues": {
          "type": "text"
        }
      },
      "defaultValue": {
        "type": "objectParameterPropertyValue",
        "objectParameterPropertyValue": {
          "parameterId": "objectToModifyParameter",
          "propertyTypeId": "sarDraft"
        }
      }
    }
  ],
  "status": "active",
  "rules": [
    {
      "type": "modifyObjectRule",
      "modifyObjectRule": {
        "objectToModify": "objectToModifyParameter",
        "propertyValues": {
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
          "sarDraft": {
            "type": "parameterId",
            "parameterId": "sarDraft"
          }
        },
        "structFieldValues": {}
      }
    }
  ],
  "entities": {
    "affectedInterfaceTypes": [],
    "affectedObjectTypes": [
      "aml.amlInvestigationCase"
    ],
    "affectedLinkTypes": [],
    "typeGroups": []
  },
  "parameterOrdering": [
    "objectToModifyParameter",
    "caseStatus",
    "analystNotes",
    "sarRequired",
    "sarDraft"
  ],
  "__type": OntologyEntityTypeEnum.ACTION_TYPE
} as unknown as ActionType;
        
export const amlUpdateCase: ActionType = wrapWithProxy(amlUpdateCase_base);
        