from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Optional
from datetime import datetime, timezone


class RiskLevel(str, Enum):
    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class DecisionRecommendation(str, Enum):
    APPROVE = "APPROVE"
    FLAGGED = "FLAGGED"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class RiskFactor(BaseModel):
    feature: str = Field(..., description="Feature name that influenced the score")
    contribution: float = Field(..., description="Relative contribution weight / feature importance")
    description: str = Field(..., description="Human-readable explanation of risk influence")


class PredictionResponse(BaseModel):
    transaction_ref: Optional[str] = Field(None, description="Echoed transaction reference")
    fraud_probability: float = Field(..., ge=0.0, le=1.0, description="Predicted probability of fraud [0.0 - 1.0]")
    risk_level: RiskLevel = Field(..., description="Qualitative risk classification: APPROVE, REVIEW, or BLOCK")
    recommendation: DecisionRecommendation = Field(..., description="Recommended action based on calibrated thresholds")
    model_version: str = Field(..., description="Model artifact identifier")
    risk_factors: List[RiskFactor] = Field(default_factory=list, description="Top influential features explaining the decision")
    evaluated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="Scoring timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_ref": "TX-948201",
                "fraud_probability": 0.8679,
                "risk_level": "BLOCK",
                "recommendation": "BLOCK",
                "model_version": "v1.0.0-trained",
                "risk_factors": [
                    {
                        "feature": "V258",
                        "contribution": 0.135,
                        "description": "Critical behavioral payment velocity deviation (V258=3.0)"
                    },
                    {
                        "feature": "C13",
                        "contribution": 0.076,
                        "description": "High transaction frequency associated with card (C13=15.0)"
                    }
                ],
                "evaluated_at": "2026-09-17T07:30:00Z"
            }
        }
