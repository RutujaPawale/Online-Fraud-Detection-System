from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "Fraud Detection ML Service"
    API_V1_STR: str = "/api/v1"
    MODEL_VERSION: str = "v1.0.0-trained"
    MODEL_PATH: str = "models/fraud_model.joblib"
    PREPROCESSOR_PATH: str = "models/preprocessor.joblib"
    METRICS_PATH: str = "models/metrics.json"
    CORS_ORIGINS: List[str] = ["*"]
    
    # Calibrated decision thresholds
    LOW_RISK_THRESHOLD: float = 0.30   # prob < 0.30 -> APPROVE
    HIGH_RISK_THRESHOLD: float = 0.85  # prob >= 0.85 -> BLOCK; [0.30 - 0.85) -> REVIEW

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
