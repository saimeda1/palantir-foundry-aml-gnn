
import { wrapWithProxy, OntologyEntityTypeEnum } from '@osdk/maker';
import type { ActionType } from '@osdk/maker';

/** @type {import('@osdk/maker').ActionType} */
const amlAssignAlertToCase_base: ActionType = {
  "apiName": "aml.aml-assign-alert-to-case",
  "displayName": "Assign Alert to Case",
  "description": "Escalate: set case_id and status = Escalated.",
  "parameters": [
    {
      "id": "objectToModifyParameter",
      "displayName": "Modify object",
      "type": {
        "type": "objectReference",
        "objectReference": {
          "objectTypeId": "aml.amlAlert"
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
      "id": "status",
      "displayName": "Status",
      "type": "string",
      "validation": {
        "allowedValues": {
          "type": "oneOf",
          "oneOf": [
            {
              "label": "Escalated",
              "value": {
                "type": "string",
                "string": "Escalated"
              }
            }
          ]
        },
        "defaultValue": {
          "type": "staticValue",
          "staticValue": {
            "type": "string",
            "string": "Escalated"
          }
        },
        "required": false
      },
      "defaultValue": {
        "type": "staticValue",
        "staticValue": {
          "type": "string",
          "string": "Escalated"
        }
      }
    },
    {
      "id": "caseId",
      "displayName": "Case ID",
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
          "propertyTypeId": "caseId"
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
          "status": {
            "type": "parameterId",
            "parameterId": "status"
          },
          "caseId": {
            "type": "parameterId",
            "parameterId": "caseId"
          }
        },
        "structFieldValues": {}
      }
    }
  ],
  "entities": {
    "affectedInterfaceTypes": [],
    "affectedObjectTypes": [
      "aml.amlAlert"
    ],
    "affectedLinkTypes": [],
    "typeGroups": []
  },
  "parameterOrdering": [
    "objectToModifyParameter",
    "status",
    "caseId"
  ],
  "__type": OntologyEntityTypeEnum.ACTION_TYPE
} as unknown as ActionType;
        
export const amlAssignAlertToCase: ActionType = wrapWithProxy(amlAssignAlertToCase_base);
        