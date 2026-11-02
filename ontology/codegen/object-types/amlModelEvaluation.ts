
import { wrapWithProxy, OntologyEntityTypeEnum } from '@osdk/maker';
import type { ObjectType } from '@osdk/maker';

/** @type {import('@osdk/maker').ObjectType} */
const amlModelEvaluation_base: ObjectType = {
  "apiName": "aml.amlModelEvaluation",
  "displayName": "Model Evaluation",
  "pluralDisplayName": "Model Evaluations",
  "primaryKeyPropertyApiName": "metric",
  "titlePropertyApiName": "metric",
  "description": "Precision/recall per risk band and precision@K on the labeled test stream.",
  "icon": {
    "locator": "timeline-bar-chart",
    "color": "#5C7080"
  },
  "datasources": [
    {
      "type": "dataset"
    }
  ],
  "properties": [
    {
      "type": "string",
      "displayName": "Metric",
      "apiName": "metric"
    },
    {
      "type": "integer",
      "displayName": "N",
      "apiName": "n"
    },
    {
      "type": "double",
      "displayName": "Precision",
      "apiName": "precision"
    },
    {
      "type": "double",
      "displayName": "Recall",
      "apiName": "recall"
    },
    {
      "type": "string",
      "displayName": "Model Version",
      "apiName": "modelVersion"
    },
    {
      "type": "integer",
      "displayName": "Positives",
      "apiName": "positives"
    },
    {
      "type": "integer",
      "displayName": "Total",
      "apiName": "total"
    }
  ],
  "__type": OntologyEntityTypeEnum.OBJECT_TYPE
} as unknown as ObjectType;
        
export const amlModelEvaluation: ObjectType = wrapWithProxy(amlModelEvaluation_base);
        