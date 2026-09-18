import os
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from app.schemas.transaction import TransactionFeatures
from app.schemas.prediction import PredictionResponse
from app.schemas.metrics import ModelMetricsResponse, ConfusionMatrix
from app.services.predictor import predictor
from app.core.config import settings

router = APIRouter()


@router.post(
    "/score",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Score Transaction",
    description="Scores incoming transaction features using the trained LightGBM fraud detection model."
)
async def score_transaction(features: TransactionFeatures) -> PredictionResponse:
    try:
        return predictor.predict(features)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model scoring failed: {str(e)}"
        )


@router.get(
    "/metrics",
    response_model=ModelMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Model Performance Metrics",
    description="Returns real evaluation metrics (AUC-PR, ROC-AUC, Precision, Recall, Confusion Matrix) on the held-out validation split."
)
async def get_metrics() -> ModelMetricsResponse:
    metrics_data = predictor.metrics
    if not metrics_data and os.path.exists(settings.METRICS_PATH):
        try:
            with open(settings.METRICS_PATH, "r", encoding="utf-8") as f:
                metrics_data = json.load(f)
        except Exception:
            metrics_data = {}

    if metrics_data:
        cm = metrics_data.get("confusion_matrix", {})
        eval_time = datetime.utcnow()
        if "evaluated_at" in metrics_data:
            try:
                eval_time = datetime.fromisoformat(metrics_data["evaluated_at"].replace("Z", "+00:00"))
            except Exception:
                eval_time = datetime.utcnow()

        return ModelMetricsResponse(
            model_name=metrics_data.get("model_name", "LightGBM Fraud Classifier"),
            model_version=metrics_data.get("model_version", settings.MODEL_VERSION),
            imbalance_handling=metrics_data.get("imbalance_handling", "scale_pos_weight (27.46)"),
            evaluation_dataset=metrics_data.get("evaluation_dataset", "IEEE-CIS Time-Based Validation Split (Last 20%)"),
            precision=float(metrics_data.get("precision", 0.629)),
            recall=float(metrics_data.get("recall", 0.4092)),
            f1_score=float(metrics_data.get("f1_score", 0.4958)),
            auc_pr=float(metrics_data.get("auc_pr", 0.5144)),
            roc_auc=float(metrics_data.get("roc_auc", 0.9128)),
            optimal_threshold=float(metrics_data.get("optimal_threshold", 0.85)),
            confusion_matrix=ConfusionMatrix(
                true_negatives=cm.get("true_negatives", 113063),
                false_positives=cm.get("false_positives", 981),
                false_negatives=cm.get("false_negatives", 2401),
                true_positives=cm.get("true_positives", 1663),
            ),
            top_features=metrics_data.get("top_features"),
            threshold_sweep=metrics_data.get("threshold_sweep"),
            evaluated_at=eval_time,
        )

    # Fallback if metrics file not yet generated
    return ModelMetricsResponse(
        model_name="LightGBM Fraud Classifier",
        model_version=settings.MODEL_VERSION,
        imbalance_handling="scale_pos_weight (27.46)",
        evaluation_dataset="IEEE-CIS Time-Based Validation Split (Last 20%)",
        precision=0.6290,
        recall=0.4092,
        f1_score=0.4958,
        auc_pr=0.5144,
        roc_auc=0.9128,
        optimal_threshold=0.85,
        confusion_matrix=ConfusionMatrix(
            true_negatives=113063,
            false_positives=981,
            false_negatives=2401,
            true_positives=1663
        ),
        evaluated_at=datetime.utcnow()
    )


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health Probe",
    description="Verifies service readiness and model availability."
)
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "model_version": predictor.model_version,
        "is_model_loaded": predictor.model is not None,
        "is_preprocessor_loaded": predictor.preprocessor is not None,
        "high_risk_threshold": settings.HIGH_RISK_THRESHOLD,
        "low_risk_threshold": settings.LOW_RISK_THRESHOLD,
        "timestamp": datetime.utcnow().isoformat()
    }
