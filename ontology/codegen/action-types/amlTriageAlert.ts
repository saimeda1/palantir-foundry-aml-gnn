
import { wrapWithProxy, OntologyEntityTypeEnum } from '@osdk/maker';
import type { ActionType } from '@osdk/maker';

/** @type {import('@osdk/maker').ActionType} */
const amlTriageAlert_base: ActionType = {
  "apiName": "aml.aml-triage-alert",
  "displayName": "Triage Alert",
  "description": "Mark an open alert as triaged.",
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
              "label": "Triaged",
              "value": {
                "type": "string",
                "string": "Triaged"
              }
            }
          ]
        },
        "defaultValue": {
          "type": "staticValue",
          "staticValue": {
            "type": "string",
            "string": "Triaged"
          }
        },
        "required": false
      },
      "defaultValue": {
        "type": "staticValue",
        "staticValue": {
          "type": "string",
          "string": "Triaged"
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
    "status"
  ],
  "__type": OntologyEntityTypeEnum.ACTION_TYPE
} as unknown as ActionType;
        
export const amlTriageAlert: ActionType = wrapWithProxy(amlTriageAlert_base);
        