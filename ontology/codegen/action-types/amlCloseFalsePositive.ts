
import { wrapWithProxy, OntologyEntityTypeEnum } from '@osdk/maker';
import type { ActionType } from '@osdk/maker';

/** @type {import('@osdk/maker').ActionType} */
const amlCloseFalsePositive_base: ActionType = {
  "apiName": "aml.aml-close-false-positive",
  "displayName": "Close as False Positive",
  "description": "Close an alert; the disposition feeds model retraining.",
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
            "string": "Closed"
          }
        },
        "required": false
      },
      "defaultValue": {
        "type": "staticValue",
        "staticValue": {
          "type": "string",
          "string": "Closed"
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
        
export const amlCloseFalsePositive: ActionType = wrapWithProxy(amlCloseFalsePositive_base);
        