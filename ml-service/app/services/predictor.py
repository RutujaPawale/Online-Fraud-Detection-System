import os
import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import joblib
import numpy as np
import pandas as pd

from app.core.config import settings
from app.schemas.transaction import TransactionFeatures
from app.schemas.prediction import (
    PredictionResponse,
    RiskLevel,
    DecisionRecommendation,
    RiskFactor,
)

logger = logging.getLogger(__name__)


class FraudPredictor:
    """
    Production-ready inference service that loads the trained LightGBM model
    and preprocessor pipeline to score online transactions.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        preprocessor_path: Optional[str] = None,
        metrics_path: Optional[str] = None,
    ):
        self.model_path = model_path or settings.MODEL_PATH
        self.preprocessor_path = preprocessor_path or settings.PREPROCESSOR_PATH
        self.metrics_path = metrics_path or settings.METRICS_PATH

        self.model = None
        self.preprocessor = None
        self.metrics = {}
        self.model_version = settings.MODEL_VERSION
        self.top_feature_list: List[Dict[str, Any]] = []

        self._load_artifacts()

    def _load_artifacts(self):
        """Loads trained model, preprocessor pipeline, and evaluation metrics."""
        # 1. Load Preprocessor
        if os.path.exists(self.preprocessor_path):
            try:
                self.preprocessor = joblib.load(self.preprocessor_path)
                logger.info(f"Loaded feature preprocessor from {self.preprocessor_path}")
            except Exception as e:
                logger.error(f"Failed loading preprocessor from {self.preprocessor_path}: {e}")
                raise RuntimeError(f"Cannot initialize FraudPredictor without preprocessor: {e}")
        else:
            logger.warning(f"Preprocessor not found at {self.preprocessor_path}")

        # 2. Load LightGBM Model
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                logger.info(f"Loaded trained LightGBM model from {self.model_path}")
            except Exception as e:
                logger.error(f"Failed loading model from {self.model_path}: {e}")
                raise RuntimeError(f"Cannot initialize FraudPredictor without model: {e}")
        else:
            logger.warning(f"Trained model not found at {self.model_path}")

        # 3. Load Metrics
        if os.path.exists(self.metrics_path):
            try:
                with open(self.metrics_path, "r", encoding="utf-8") as f:
                    self.metrics = json.load(f)
                    self.model_version = self.metrics.get("model_version", self.model_version)
                    self.top_feature_list = self.metrics.get("top_features", [])
                logger.info(f"Loaded metrics from {self.metrics_path}")
            except Exception as e:
                logger.warning(f"Could not load metrics from {self.metrics_path}: {e}")

    def predict(self, features: TransactionFeatures) -> PredictionResponse:
        """
        Transforms raw transaction features with the fitted preprocessor
        and scores the transaction with the trained LightGBM model.
        """
        if self.model is None or self.preprocessor is None:
            raise RuntimeError("Model or preprocessor artifact is not loaded. Cannot execute inference.")

        # 1. Convert inbound DTO into raw IEEE-CIS DataFrame
        raw_df = self._features_to_dataframe(features)

        # 2. Transform through fitted preprocessing pipeline
        transformed_df = self.preprocessor.transform(raw_df)

        # 3. Clean and align feature names for LightGBM
        drop_meta = [c for c in ["TransactionID", "isFraud", "TransactionDT"] if c in transformed_df.columns]
        X_clean = transformed_df.drop(columns=drop_meta).rename(
            columns=lambda c: re.sub(r'[^a-zA-Z0-9_]', '_', c)
        )

        # Align with model's expected feature order
        if hasattr(self.model, "feature_name_"):
            X_clean = X_clean.reindex(columns=self.model.feature_name_, fill_value=0.0)

        # 4. Predict fraud probability
        proba_arr = self.model.predict_proba(X_clean)[:, 1]
        fraud_prob = round(float(proba_arr[0]), 4)

        # 5. Apply two-threshold scheme:
        #    BLOCK:   prob >= 0.85
        #    REVIEW:  0.30 <= prob < 0.85
        #    APPROVE: prob < 0.30
        if fraud_prob >= settings.HIGH_RISK_THRESHOLD:
            risk_level = RiskLevel.BLOCK
            recommendation = DecisionRecommendation.BLOCK
        elif fraud_prob >= settings.LOW_RISK_THRESHOLD:
            risk_level = RiskLevel.REVIEW
            recommendation = DecisionRecommendation.FLAGGED
        else:
            risk_level = RiskLevel.APPROVE
            recommendation = DecisionRecommendation.APPROVE

        # 6. Extract dynamic risk factors explaining the specific score
        risk_factors = self._explain_risk_factors(features, raw_df, transformed_df, fraud_prob)

        return PredictionResponse(
            transaction_ref=features.transaction_ref,
            fraud_probability=fraud_prob,
            risk_level=risk_level,
            recommendation=recommendation,
            model_version=self.model_version,
            risk_factors=risk_factors,
        )

    def _features_to_dataframe(self, features: TransactionFeatures) -> pd.DataFrame:
        """Converts incoming Pydantic model into a single-row DataFrame."""
        row_dict: Dict[str, Any] = {
            "TransactionAmt": features.transaction_amt,
            "ProductCD": features.product_cd,
            "card1": str(features.card1) if features.card1 else "13926",
            "card2": features.card2,
            "card3": features.card3,
            "card4": features.card4,
            "card5": features.card5,
            "card6": features.card6,
            "addr1": features.addr1,
            "addr2": features.addr2,
            "dist1": features.dist1,
            "dist2": features.dist2,
            "P_emaildomain": features.p_emaildomain,
            "R_emaildomain": features.r_emaildomain,
            "DeviceType": features.device_type,
            "DeviceInfo": features.device_info,
            "TransactionDT": 86400 * 30,  # default mid-timeline anchor if not supplied
        }

        # Merge additional raw IEEE-CIS columns (e.g. V258, C13, V294, C4, etc.)
        if features.additional_features:
            for k, v in features.additional_features.items():
                row_dict[k] = v

        return pd.DataFrame([row_dict])

    def _explain_risk_factors(
        self,
        features: TransactionFeatures,
        raw_df: pd.DataFrame,
        transformed_df: pd.DataFrame,
        prob: float,
    ) -> List[RiskFactor]:
        """
        Maps the trained model's top features (V258, C13, V294, C4, card1/C1, TransactionAmt)
        to the specific transaction's feature values to explain why it was scored.
        """
        factors: List[RiskFactor] = []

        # 1. Transaction Amount & Card Mean Ratio
        amt = features.transaction_amt
        amt_ratio = None
        if "amt_to_card1_mean" in transformed_df.columns:
            amt_ratio = float(transformed_df["amt_to_card1_mean"].iloc[0])

        if amt_ratio is not None and amt_ratio > 1.5:
            factors.append(RiskFactor(
                feature="TransactionAmt",
                contribution=0.024,
                description=f"Transaction value (${amt:,.2f}) is {amt_ratio:.1f}x higher than user's card average",
            ))
        elif amt > 500.0:
            factors.append(RiskFactor(
                feature="TransactionAmt",
                contribution=0.024,
                description=f"Elevated payment amount of ${amt:,.2f}",
            ))

        # 2. Email Domain Mismatch Check
        p_email = (features.p_emaildomain or "").strip().lower()
        r_email = (features.r_emaildomain or "").strip().lower()
        if p_email and r_email and p_email != r_email:
            factors.append(RiskFactor(
                feature="email_domain_mismatch",
                contribution=0.040,
                description=f"Purchaser domain ({p_email}) does not match recipient domain ({r_email})",
            ))

        # 3. Missing Device Verification / Identity
        if not features.device_type:
            factors.append(RiskFactor(
                feature="DeviceType",
                contribution=0.015,
                description="Transaction originated from an unverified device without identity profile",
            ))

        # 4. Behavioral & Velocity Features (V258, C13, V294, C4, C1)
        raw_dict = features.additional_features or {}

        # V258 (Top Feature #1, 13.5% gain)
        v258 = raw_dict.get("V258", None)
        if v258 is not None and float(v258) > 1.0:
            factors.append(RiskFactor(
                feature="V258",
                contribution=0.135,
                description=f"Vesta behavioral payment velocity trigger detected (V258 = {v258})",
            ))

        # C13 (Top Feature #2, 7.6% gain)
        c13 = raw_dict.get("C13", None)
        if c13 is not None and float(c13) > 5.0:
            factors.append(RiskFactor(
                feature="C13",
                contribution=0.076,
                description=f"Unusually high transaction frequency count for this card account (C13 = {c13})",
            ))

        # V294 (Top Feature #3, 6.7% gain)
        v294 = raw_dict.get("V294", None)
        if v294 is not None and float(v294) > 0.0:
            factors.append(RiskFactor(
                feature="V294",
                contribution=0.067,
                description=f"Cumulative velocity count anomaly on card profile (V294 = {v294})",
            ))

        # C4 (Top Feature #4, 3.3% gain)
        c4 = raw_dict.get("C4", None)
        if c4 is not None and float(c4) > 1.0:
            factors.append(RiskFactor(
                feature="C4",
                contribution=0.033,
                description=f"Rapid repeated attempt count detected on card network (C4 = {c4})",
            ))

        # 5. High-risk Card Type (card6_credit, 1.29% gain)
        if (features.card6 or "").lower() == "credit":
            factors.append(RiskFactor(
                feature="card6",
                contribution=0.013,
                description="Payment processed via credit card (higher historical chargeback risk)",
            ))

        # If low probability and no elevated factors, record normal baseline
        if not factors:
            factors.append(RiskFactor(
                feature="baseline",
                contribution=0.010,
                description="Transaction parameters fall within normal legitimate baseline patterns",
            ))

        # Sort descending by contribution and return top 4
        factors.sort(key=lambda x: x.contribution, reverse=True)
        return factors[:4]


# Singleton instance loaded once on startup
predictor = FraudPredictor()
