from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime


class ConfusionMatrix(BaseModel):
    true_negatives: int = Field(..., description="Legitimate transactions correctly approved")
    false_positives: int = Field(..., description="Legitimate transactions incorrectly flagged/blocked")
    false_negatives: int = Field(..., description="Fraudulent transactions missed")
    true_positives: int = Field(..., description="Fraudulent transactions correctly caught")


class ModelMetricsResponse(BaseModel):
    model_name: str = Field(default="LightGBM Fraud Classifier")
    model_version: str = Field(default="v1.0.0-trained")
    imbalance_handling: str = Field(default="scale_pos_weight (27.46)", description="Strategy used for class imbalance")
    evaluation_dataset: str = Field(default="IEEE-CIS Time-Based Validation Split (Last 20%)")
    precision: float = Field(..., description="Precision metric (TP / (TP + FP))")
    recall: float = Field(..., description="Recall / Sensitivity metric (TP / (TP + FN))")
    f1_score: float = Field(..., description="Harmonic mean of precision and recall")
    auc_pr: float = Field(..., description="Area under the Precision-Recall Curve")
    roc_auc: float = Field(..., description="Area under the Receiver Operating Characteristic")
    optimal_threshold: float = Field(default=0.85, description="Decision threshold calibrated for maximum F1")
    confusion_matrix: ConfusionMatrix
    top_features: Optional[List[Dict[str, Any]]] = Field(default=None, description="Top 20 features by information gain")
    threshold_sweep: Optional[List[Dict[str, Any]]] = Field(default=None, description="Threshold trade-off sweep table")
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "model_name": "LightGBM Fraud Classifier",
                "model_version": "v1.0.0-trained",
                "imbalance_handling": "scale_pos_weight (27.46)",
                "evaluation_dataset": "IEEE-CIS Time-Based Validation Split (Last 20%)",
                "precision": 0.629,
                "recall": 0.4092,
                "f1_score": 0.4958,
                "auc_pr": 0.5144,
                "roc_auc": 0.9128,
                "optimal_threshold": 0.85,
                "confusion_matrix": {
                    "true_negatives": 113063,
                    "false_positives": 981,
                    "false_negatives": 2401,
                    "true_positives": 1663
                },
                "evaluated_at": "2026-09-17T07:25:00Z"
            }
        }
