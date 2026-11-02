
import { wrapWithProxy, OntologyEntityTypeEnum } from '@osdk/maker';
import type { LinkType } from '@osdk/maker';

/** @type {import('@osdk/maker').LinkType} */
const amlAggregates_base: LinkType = {
  "apiName": "amlAggregates",
  "one": {
    "object": {
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
      "properties": {
        "caseId": {
          "type": "string",
          "displayName": "Case ID"
        },
        "title": {
          "type": "string",
          "displayName": "Title"
        },
        "analystNotes": {
          "type": {
            "type": "string",
            "isLongText": true
          },
          "displayName": "Analyst Notes"
        },
        "sarRequired": {
          "type": "boolean",
          "displayName": "SAR Required"
        },
        "caseStatus": {
          "type": "string",
          "displayName": "Case Status"
        },
        "openedTs": {
          "type": "timestamp",
          "displayName": "Opened At"
        },
        "sarDraft": {
          "type": {
            "type": "string",
            "isLongText": true
          },
          "displayName": "SAR Draft"
        }
      }
    },
    "metadata": {
      "apiName": "alerts",
      "displayMetadata": {
        "displayName": "Alert",
        "pluralDisplayName": "Alerts",
        "visibility": "NORMAL",
        "groupDisplayName": ""
      },
      "typeClasses": []
    }
  },
  "toMany": {
    "object": {
      "apiName": "aml.amlAlert",
      "displayName": "AML Alert",
      "pluralDisplayName": "AML Alerts",
      "primaryKeyPropertyApiName": "alertId",
      "titlePropertyApiName": "alertId",
      "description": "High/Medium-band transactions queued for investigator triage.",
      "icon": {
        "locator": "warning-sign",
        "color": "#CD4246"
      },
      "editsEnabled": true,
      "datasources": [
        {
          "type": "dataset"
        }
      ],
      "properties": {
        "alertId": {
          "type": "string",
          "displayName": "Alert ID"
        },
        "transactionId": {
          "type": "long",
          "displayName": "Transaction ID"
        },
        "subjectAccountId": {
          "type": "string",
          "displayName": "Subject Account"
        },
        "counterpartyAccountId": {
          "type": "string",
          "displayName": "Counterparty Account"
        },
        "status": {
          "type": "string",
          "displayName": "Status"
        },
        "priority": {
          "type": "string",
          "displayName": "Priority"
        },
        "primaryTypology": {
          "type": "string",
          "displayName": "Typology (derived)"
        },
        "launderingProbability": {
          "type": "double",
          "displayName": "Laundering Probability"
        },
        "riskBand": {
          "type": "string",
          "displayName": "Risk Band"
        },
        "amountUsd": {
          "type": "double",
          "displayName": "Amount"
        },
        "paymentFormat": {
          "type": "string",
          "displayName": "Payment Format"
        },
        "alertedTs": {
          "type": "timestamp",
          "displayName": "Alerted At"
        },
        "modelVersion": {
          "type": "string",
          "displayName": "Model Version"
        },
        "caseId": {
          "type": "string",
          "displayName": "Case ID"
        },
        "patternId": {
          "type": "string",
          "displayName": "Pattern ID (demo only)"
        },
        "trueTypology": {
          "type": "string",
          "displayName": "True Typology (demo only)"
        },
        "isLaunderingGroundTruth": {
          "type": "integer",
          "displayName": "Ground Truth (demo only)"
        }
      }
    },
    "metadata": {
      "apiName": "investigationCase",
      "displayMetadata": {
        "displayName": "Investigation Case",
        "pluralDisplayName": "Investigation Cases",
        "visibility": "NORMAL",
        "groupDisplayName": ""
      },
      "typeClasses": []
    }
  },
  "manyForeignKeyProperty": "caseId",
  "__type": OntologyEntityTypeEnum.LINK_TYPE
} as unknown as LinkType;
        
export const amlAggregates: LinkType = wrapWithProxy(amlAggregates_base);
        