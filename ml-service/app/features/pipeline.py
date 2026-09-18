import os
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder

from app.features.transformers import (
    FraudDomainFeatureEngineer,
    SparseMissingIndicator,
    MatchFlagEncoder,
    EmailDomainGrouper,
)

# Default path for serialized preprocessor
CURRENT_DIR = Path(__file__).resolve().parent
ML_SERVICE_ROOT = CURRENT_DIR.parents[1]
DEFAULT_MODEL_PATH = ML_SERVICE_ROOT / "models" / "preprocessor.joblib"


class FraudFeaturePipeline(BaseEstimator, TransformerMixin):
    """
    End-to-End Inference-Ready Preprocessing Pipeline for Fraud Detection.
    Handles:
    1. Domain feature engineering (z-scores, time deltas, email mismatches)
    2. Missingness flags & sparse column reduction
    3. Match flag encoding (M1-M9)
    4. Email domain long-tail grouping
    5. Median imputation for numeric features
    6. Missing-category imputation + One-Hot Encoding for categorical features
    """

    def __init__(
        self,
        missing_threshold: float = 0.85,
        top_n_email: int = 15,
        categorical_cols: Optional[List[str]] = None,
    ):
        self.missing_threshold = missing_threshold
        self.top_n_email = top_n_email
        self.explicit_categorical_cols = categorical_cols or [
            "ProductCD", "card4", "card6", "DeviceType",
            "P_emaildomain", "R_emaildomain"
        ]

        # Sub-transformers
        self.domain_engineer = FraudDomainFeatureEngineer()
        self.sparse_indicator = SparseMissingIndicator(missing_threshold=self.missing_threshold)
        self.match_encoder = MatchFlagEncoder()
        self.email_grouper = EmailDomainGrouper(top_n=self.top_n_email)

        # Imputers and encoders learned during fit
        self.numeric_cols_: List[str] = []
        self.categorical_cols_: List[str] = []
        self.numeric_imputer_ = SimpleImputer(strategy="median")
        self.cat_imputer_ = SimpleImputer(strategy="constant", fill_value="missing")
        self.cat_encoder_ = OneHotEncoder(
            handle_unknown="ignore",
            sparse_output=False,
            max_categories=15
        )
        self.encoded_cat_feature_names_: List[str] = []
        self.all_feature_names_out_: List[str] = []

    def fit(self, X: pd.DataFrame, y=None):
        df = X.copy() if isinstance(X, pd.DataFrame) else pd.DataFrame(X).copy()

        # Isolate metadata/target if present
        df_work = df.drop(columns=[c for c in ["isFraud", "TransactionID"] if c in df.columns])

        # Step 1: Domain Features
        df_work = self.domain_engineer.fit(df_work, y).transform(df_work)

        # Step 2: Sparse Indicators & Dropping
        df_work = self.sparse_indicator.fit(df_work, y).transform(df_work)

        # Step 3: Match Flags
        df_work = self.match_encoder.fit(df_work, y).transform(df_work)

        # Step 4: Email Grouping
        df_work = self.email_grouper.fit(df_work, y).transform(df_work)

        # Step 5: Identify Categorical and Numeric Columns
        cat_candidates = [c for c in self.explicit_categorical_cols if c in df_work.columns]
        other_cats = df_work.select_dtypes(include=["object", "category"]).columns.tolist()
        self.categorical_cols_ = list(dict.fromkeys(cat_candidates + other_cats))

        self.numeric_cols_ = [
            c for c in df_work.columns
            if c not in self.categorical_cols_ and c not in ["isFraud", "TransactionID"]
        ]

        # Fit Numeric Imputer
        if self.numeric_cols_:
            self.numeric_imputer_.fit(df_work[self.numeric_cols_])

        # Fit Categorical Imputer & One-Hot Encoder
        if self.categorical_cols_:
            imputed_cats = self.cat_imputer_.fit_transform(df_work[self.categorical_cols_])
            self.cat_encoder_.fit(imputed_cats)
            self.encoded_cat_feature_names_ = list(
                self.cat_encoder_.get_feature_names_out(self.categorical_cols_)
            )

        self.all_feature_names_out_ = self.numeric_cols_ + self.encoded_cat_feature_names_
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        df = X.copy() if isinstance(X, pd.DataFrame) else pd.DataFrame(X).copy()

        # Preserve metadata / target if present
        meta_cols: Dict[str, pd.Series] = {}
        for c in ["TransactionID", "isFraud"]:
            if c in df.columns:
                meta_cols[c] = df[c]

        df_work = df.drop(columns=[c for c in ["isFraud", "TransactionID"] if c in df.columns])

        # Step 1: Domain Features
        df_work = self.domain_engineer.transform(df_work)

        # Step 2: Sparse Indicators & Dropping
        df_work = self.sparse_indicator.transform(df_work)

        # Step 3: Match Flags
        df_work = self.match_encoder.transform(df_work)

        # Step 4: Email Grouping
        df_work = self.email_grouper.transform(df_work)

        # Ensure all expected numeric columns exist in input
        missing_num = [c for c in self.numeric_cols_ if c not in df_work.columns]
        if missing_num:
            df_work = pd.concat([df_work, pd.DataFrame(np.nan, index=df_work.index, columns=missing_num)], axis=1)

        # Transform Numerics
        if self.numeric_cols_:
            num_data = self.numeric_imputer_.transform(df_work[self.numeric_cols_])
            num_df = pd.DataFrame(num_data, columns=self.numeric_cols_, index=df_work.index)
        else:
            num_df = pd.DataFrame(index=df_work.index)

        # Ensure all expected categorical columns exist in input
        missing_cat = [c for c in self.categorical_cols_ if c not in df_work.columns]
        if missing_cat:
            df_work = pd.concat([df_work, pd.DataFrame("missing", index=df_work.index, columns=missing_cat)], axis=1)

        # Transform Categoricals
        if self.categorical_cols_:
            cat_imputed = self.cat_imputer_.transform(df_work[self.categorical_cols_])
            cat_encoded = self.cat_encoder_.transform(cat_imputed)
            cat_df = pd.DataFrame(
                cat_encoded,
                columns=self.encoded_cat_feature_names_,
                index=df_work.index
            )
        else:
            cat_df = pd.DataFrame(index=df_work.index)

        # Combine Transformed Features
        transformed_df = pd.concat([num_df, cat_df], axis=1)

        # Restore preserved metadata at the front
        for c, series in reversed(meta_cols.items()):
            transformed_df.insert(0, c, series)

        return transformed_df

    def get_feature_names_out(self, input_features=None) -> List[str]:
        return self.all_feature_names_out_


def build_feature_pipeline(
    missing_threshold: float = 0.85,
    top_n_email: int = 15
) -> FraudFeaturePipeline:
    return FraudFeaturePipeline(
        missing_threshold=missing_threshold,
        top_n_email=top_n_email
    )


def fit_and_save_pipeline(
    df: pd.DataFrame,
    output_model_path: Optional[Path | str] = None,
    missing_threshold: float = 0.85,
    top_n_email: int = 15
) -> Tuple[FraudFeaturePipeline, pd.DataFrame]:
    """
    Fits the feature pipeline on the dataset, saves the fitted transformer to joblib,
    and returns both the fitted pipeline and the transformed DataFrame.
    """
    out_path = Path(output_model_path) if output_model_path else DEFAULT_MODEL_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[*] Building and fitting FraudFeaturePipeline (missing_threshold={missing_threshold})...")
    pipeline = build_feature_pipeline(missing_threshold=missing_threshold, top_n_email=top_n_email)
    pipeline.fit(df)

    print(f"[*] Serializing fitted pipeline to {out_path}...")
    joblib.dump(pipeline, out_path)
    print(f"[+] Pipeline successfully saved! ({os.path.getsize(out_path) / (1024**2):.2f} MB)")

    print(f"[*] Transforming training dataset...")
    transformed_df = pipeline.transform(df)
    return pipeline, transformed_df
