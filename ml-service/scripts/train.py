"""
Script to execute the LightGBM fraud model training pipeline.

Usage:
    python scripts/train.py
    python scripts/train.py --n-estimators 200 --learning-rate 0.05
"""

import sys
import argparse
from pathlib import Path

# Add ml-service root to python path
ML_SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(ML_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_SERVICE_ROOT))

from app.training.train_model import run_training_pipeline


def main():
    parser = argparse.ArgumentParser(description="Train LightGBM Fraud Detection Model.")
    parser.add_argument(
        "--data-path",
        type=str,
        default=str(ML_SERVICE_ROOT / "data" / "processed" / "train_features.parquet"),
        help="Path to train_features.parquet."
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default=str(ML_SERVICE_ROOT / "models" / "fraud_model.joblib"),
        help="Path to save fraud_model.joblib."
    )
    parser.add_argument(
        "--metrics-path",
        type=str,
        default=str(ML_SERVICE_ROOT / "models" / "metrics.json"),
        help="Path to save metrics.json."
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.20,
        help="Fraction of dataset held out chronologically for validation."
    )
    parser.add_argument(
        "--n-estimators",
        type=int,
        default=300,
        help="Maximum boosting trees."
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=0.05,
        help="Boosting learning rate."
    )
    parser.add_argument(
        "--num-leaves",
        type=int,
        default=63,
        help="Max leaves per tree."
    )

    args = parser.parse_args()

    print(f"\n========================================================")
    print(f"      Fraud Detection - Model Training & Evaluation     ")
    print(f"========================================================")

    run_training_pipeline(
        data_path=args.data_path,
        model_path=args.model_path,
        metrics_path=args.metrics_path,
        val_ratio=args.val_ratio,
        n_estimators=args.n_estimators,
        learning_rate=args.learning_rate,
        num_leaves=args.num_leaves,
    )

    print("[+] Model training, threshold calibration, and metrics persistence complete!\n")


if __name__ == "__main__":
    main()
