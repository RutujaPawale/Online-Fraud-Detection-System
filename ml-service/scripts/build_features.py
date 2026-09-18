"""
Script to fit the Feature Engineering Pipeline on train_merged.parquet,
serialize the fitted preprocessor to models/preprocessor.joblib,
and save the transformed feature matrix to data/processed/train_features.parquet.

Usage:
    python scripts/build_features.py
    python scripts/build_features.py --sample 50000   # For quick verification run
"""

import sys
import os
import argparse
from pathlib import Path
import pandas as pd

# Add ml-service root to python path
ML_SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(ML_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_SERVICE_ROOT))

from app.features.pipeline import fit_and_save_pipeline


def main():
    parser = argparse.ArgumentParser(description="Build and fit feature engineering pipeline.")
    parser.add_argument(
        "--input-parquet",
        type=str,
        default=str(ML_SERVICE_ROOT / "data" / "processed" / "train_merged.parquet"),
        help="Path to train_merged.parquet input."
    )
    parser.add_argument(
        "--output-features",
        type=str,
        default=str(ML_SERVICE_ROOT / "data" / "processed" / "train_features.parquet"),
        help="Path to save train_features.parquet."
    )
    parser.add_argument(
        "--output-model",
        type=str,
        default=str(ML_SERVICE_ROOT / "models" / "preprocessor.joblib"),
        help="Path to save preprocessor.joblib."
    )
    parser.add_argument(
        "--missing-threshold",
        type=float,
        default=0.85,
        help="Missingness threshold (0.0 - 1.0) above which ultra-sparse columns are dropped."
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Optional row sample size for quick dry-runs."
    )

    args = parser.parse_args()

    input_path = Path(args.input_parquet)
    if not input_path.exists():
        print(f"[!] Input file {input_path} not found! Please run scripts/explore.py first.")
        sys.exit(1)

    print(f"\n========================================================")
    print(f"      Fraud Detection - Feature Engineering Pipeline    ")
    print(f"========================================================")
    print(f"[*] Reading merged data from: {input_path}...")
    df = pd.read_parquet(input_path)

    if args.sample and args.sample < len(df):
        print(f"[!] Subsampling to {args.sample:,} rows for rapid verification...")
        df = df.iloc[:args.sample].copy()

    print(f"    Input dataset dimensions: {df.shape[0]:,} rows x {df.shape[1]:,} columns")

    # Fit pipeline, serialize preprocessor, and transform dataset
    pipeline, transformed_df = fit_and_save_pipeline(
        df,
        output_model_path=args.output_model,
        missing_threshold=args.missing_threshold,
        top_n_email=15
    )

    # Save transformed features to Parquet
    out_features_path = Path(args.output_features)
    out_features_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[*] Saving transformed features to {out_features_path}...")
    transformed_df.to_parquet(out_features_path, engine="pyarrow", index=False)
    size_mb = os.path.getsize(out_features_path) / (1024 ** 2)
    print(f"[+] Saved train_features.parquet ({size_mb:.2f} MB)")

    # Diagnostics and Sample Display
    print("\n" + "=" * 80)
    print("                TRANSFORMATION PIPELINE DIAGNOSTICS")
    print("=" * 80)
    print(f"--- 1. Dimensions Summary ---")
    print(f"  Original shape:      {df.shape}")
    print(f"  Transformed shape:   {transformed_df.shape}")
    print(f"  Sparse columns dropped (>={args.missing_threshold*100:.0f}% null): {len(pipeline.sparse_indicator.cols_to_drop_)}")
    print(f"  Active missingness indicators added:  {len(pipeline.sparse_indicator.active_indicators_)}")
    print(f"  Numeric features imputed (median):    {len(pipeline.numeric_cols_)}")
    print(f"  One-hot encoded categorical features: {len(pipeline.encoded_cat_feature_names_)}")
    print(f"  Total final feature columns:          {transformed_df.shape[1] - 2} (excluding TransactionID & isFraud)")

    print(f"\n--- 2. Sample of Domain Engineered Features ---")
    domain_cols = [
        "amt_to_card1_mean", "amt_card1_zscore", "time_since_last_tx",
        "transaction_hour", "transaction_day", "email_domain_mismatch",
        "has_identity", "has_recipient_email"
    ]
    present_domain = [c for c in domain_cols if c in transformed_df.columns]
    print(transformed_df[present_domain].head(5).to_string())

    print(f"\n--- 3. Sample of Active Missingness Indicators ---")
    missing_cols = [f"is_missing_{c}" for c in pipeline.sparse_indicator.active_indicators_ if f"is_missing_{c}" in transformed_df.columns]
    print(transformed_df[missing_cols[:6]].head(5).to_string())

    print(f"\n--- 4. Sample of One-Hot Encoded Categoricals ---")
    sample_ohe = pipeline.encoded_cat_feature_names_[:8]
    print(transformed_df[sample_ohe].head(5).to_string())

    print(f"\n--- 5. Verification of Nulls in Transformed Features ---")
    feature_cols = [c for c in transformed_df.columns if c not in ["TransactionID", "isFraud"]]
    remaining_nulls = transformed_df[feature_cols].isnull().sum().sum()
    print(f"  Remaining null values in feature matrix: {remaining_nulls}")
    if remaining_nulls == 0:
        print("  [OK] Clean matrix: All features successfully imputed and encoded.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
