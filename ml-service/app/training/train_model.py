import os
import re
import json
import warnings
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any

import joblib
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
    roc_auc_score,
    confusion_matrix,
)

# Suppress deprecation and user warnings for clean console outputs
warnings.filterwarnings("ignore")

# Default project paths
CURRENT_DIR = Path(__file__).resolve().parent
ML_SERVICE_ROOT = CURRENT_DIR.parents[1]
DEFAULT_DATA_FILE = ML_SERVICE_ROOT / "data" / "processed" / "train_features.parquet"
DEFAULT_MODEL_FILE = ML_SERVICE_ROOT / "models" / "fraud_model.joblib"
DEFAULT_METRICS_FILE = ML_SERVICE_ROOT / "models" / "metrics.json"


def load_and_split_data(
    data_path: Optional[Path | str] = None,
    val_ratio: float = 0.20,
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, List[str], float]:
    """
    Loads transformed features and performs a strict time-based split:
    Orders records chronologically by TransactionDT;
    Earlier (1 - val_ratio) for training, most recent val_ratio for validation.
    """
    file_path = Path(data_path) if data_path else DEFAULT_DATA_FILE
    if not file_path.exists():
        raise FileNotFoundError(f"Feature dataset not found at {file_path}")

    print(f"[*] Loading feature dataset from {file_path}...")
    df = pd.read_parquet(file_path)
    total_rows, total_cols = df.shape
    print(f"    Loaded dimensions: {total_rows:,} rows x {total_cols} columns")

    # Ensure chronological ordering by TransactionDT
    if "TransactionDT" in df.columns:
        print("[*] Sorting chronologically by TransactionDT for realistic forward validation...")
        df = df.sort_values("TransactionDT").reset_index(drop=True)

    # Time-based split index
    split_idx = int(len(df) * (1.0 - val_ratio))
    train_df = df.iloc[:split_idx]
    val_df = df.iloc[split_idx:]

    target_col = "isFraud"
    id_col = "TransactionID"
    time_col = "TransactionDT"

    # Exclude metadata and target from feature matrix
    exclude_cols = {target_col, id_col, time_col}
    raw_feature_cols = [c for c in df.columns if c not in exclude_cols]

    # Sanitize feature names to eliminate special JSON characters for LightGBM
    rename_map = {c: re.sub(r'[^a-zA-Z0-9_]', '_', c) for c in raw_feature_cols}
    feature_cols = [rename_map[c] for c in raw_feature_cols]

    X_train = train_df[raw_feature_cols].rename(columns=rename_map)
    y_train = train_df[target_col].astype(int)
    X_val = val_df[raw_feature_cols].rename(columns=rename_map)
    y_val = val_df[target_col].astype(int)

    # Calculate class distribution
    train_fraud_cnt = int(y_train.sum())
    train_legit_cnt = int(len(y_train) - train_fraud_cnt)
    train_fraud_pct = (train_fraud_cnt / len(y_train)) * 100
    imbalance_ratio = train_legit_cnt / train_fraud_cnt if train_fraud_cnt > 0 else 27.58

    val_fraud_cnt = int(y_val.sum())
    val_legit_cnt = int(len(y_val) - val_fraud_cnt)
    val_fraud_pct = (val_fraud_cnt / len(y_val)) * 100

    print(f"\n--- Chronological Split Breakdown ---")
    print(f"  Training Split (Earliest {(1-val_ratio)*100:.0f}%):   {len(X_train):,} rows")
    print(f"    - Legitimate (0): {train_legit_cnt:,} ({100-train_fraud_pct:.2f}%)")
    print(f"    - Fraudulent (1): {train_fraud_cnt:,} ({train_fraud_pct:.2f}%)")
    print(f"    - Imbalance Ratio: {imbalance_ratio:.2f} : 1")
    print(f"  Validation Split (Latest {val_ratio*100:.0f}%):     {len(X_val):,} rows")
    print(f"    - Legitimate (0): {val_legit_cnt:,} ({100-val_fraud_pct:.2f}%)")
    print(f"    - Fraudulent (1): {val_fraud_cnt:,} ({val_fraud_pct:.2f}%)")
    print(f"  Total Features:      {len(feature_cols)} predictor columns")

    return X_train, y_train, X_val, y_val, feature_cols, imbalance_ratio


def train_lightgbm(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    scale_pos_weight: float,
    n_estimators: int = 300,
    learning_rate: float = 0.05,
    num_leaves: int = 63,
    random_state: int = 42,
    n_jobs: int = -1,
) -> lgb.LGBMClassifier:
    """
    Trains a LightGBM classifier with class weighting and validation early stopping.
    """
    print(f"\n[*] Initializing LightGBM Classifier...")
    print(f"    - scale_pos_weight: {scale_pos_weight:.2f}")
    print(f"    - n_estimators:     {n_estimators}")
    print(f"    - learning_rate:    {learning_rate}")
    print(f"    - num_leaves:       {num_leaves}")

    model = lgb.LGBMClassifier(
        n_estimators=n_estimators,
        learning_rate=learning_rate,
        num_leaves=num_leaves,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        importance_type="gain",
        random_state=random_state,
        n_jobs=n_jobs,
        verbose=-1,
    )

    callbacks = [
        lgb.early_stopping(stopping_rounds=40, first_metric_only=True, verbose=True),
        lgb.log_evaluation(period=25),
    ]

    print("[*] Training model across feature space...")
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        eval_names=["valid"],
        eval_metric="auc",
        callbacks=callbacks,
    )

    best_iter = getattr(model, "best_iteration_", n_estimators)
    print(f"[+] Training completed! Best iteration: {best_iter}")
    return model


def tune_threshold(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    thresholds: Optional[List[float]] = None,
) -> Tuple[float, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Sweeps decision thresholds [0.05 - 0.90] to evaluate Precision, Recall, F1,
    and Confusion Matrix tradeoffs under severe class imbalance.
    Returns the optimal threshold maximizing F1, the full sweep table, and optimal stats.
    """
    if thresholds is None:
        thresholds = [
            0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45,
            0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90
        ]

    sweep_results = []
    best_f1 = -1.0
    optimal_threshold = 0.50
    optimal_stats: Dict[str, Any] = {}

    print("\n" + "=" * 80)
    print("                    DECISION THRESHOLD SWEEP ANALYSIS")
    print("=" * 80)
    print(f"{'Threshold':<11} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'TP (Caught)':<12} | {'FP (Alarms)':<12} | {'FN (Missed)':<12}")
    print("-" * 80)

    for t in thresholds:
        y_pred = (y_proba >= t).astype(int)
        p = precision_score(y_true, y_pred, zero_division=0)
        r = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()

        record = {
            "threshold": round(float(t), 2),
            "precision": round(float(p), 4),
            "recall": round(float(r), 4),
            "f1_score": round(float(f1), 4),
            "true_positives": int(tp),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_negatives": int(tn),
        }
        sweep_results.append(record)

        print(f"{t:<11.2f} | {p:<10.4f} | {r:<10.4f} | {f1:<10.4f} | {tp:<12,d} | {fp:<12,d} | {fn:<12,d}")

        if f1 > best_f1:
            best_f1 = f1
            optimal_threshold = t
            optimal_stats = record

    print("=" * 80)
    print(f"[+] Optimal threshold calibrated for Maximum F1-Score: {optimal_threshold:.2f}")
    print(f"    Precision: {optimal_stats['precision']:.4f} | Recall: {optimal_stats['recall']:.4f} | F1: {optimal_stats['f1_score']:.4f}")
    return optimal_threshold, sweep_results, optimal_stats


def extract_top_features(
    model: lgb.LGBMClassifier,
    feature_names: List[str],
    top_n: int = 20,
) -> List[Dict[str, Any]]:
    """
    Extracts top N features ranked by LightGBM gain importance.
    """
    importances = model.feature_importances_
    total_gain = float(importances.sum()) if importances.sum() > 0 else 1.0

    ranked_indices = np.argsort(importances)[::-1][:top_n]
    top_features = []

    for rank, idx in enumerate(ranked_indices, 1):
        feat_name = feature_names[idx]
        gain = float(importances[idx])
        pct = (gain / total_gain) * 100
        top_features.append({
            "rank": rank,
            "feature": feat_name,
            "importance_gain": round(gain, 2),
            "importance_percentage": round(pct, 2),
        })

    return top_features


def save_model_and_metrics(
    model: lgb.LGBMClassifier,
    metrics_data: Dict[str, Any],
    model_path: Optional[Path | str] = None,
    metrics_path: Optional[Path | str] = None,
):
    """
    Persists trained model artifact and JSON evaluation metrics.
    """
    out_model = Path(model_path) if model_path else DEFAULT_MODEL_FILE
    out_metrics = Path(metrics_path) if metrics_path else DEFAULT_METRICS_FILE

    out_model.parent.mkdir(parents=True, exist_ok=True)
    out_metrics.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n[*] Saving trained model artifact to {out_model}...")
    joblib.dump(model, out_model)
    model_size_mb = os.path.getsize(out_model) / (1024 ** 2)
    print(f"[+] Saved fraud_model.joblib ({model_size_mb:.2f} MB)")

    print(f"[*] Saving evaluation metrics to {out_metrics}...")
    with open(out_metrics, "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)
    print(f"[+] Saved metrics.json ({os.path.getsize(out_metrics)} bytes)")


def run_training_pipeline(
    data_path: Optional[Path | str] = None,
    model_path: Optional[Path | str] = None,
    metrics_path: Optional[Path | str] = None,
    val_ratio: float = 0.20,
    n_estimators: int = 300,
    learning_rate: float = 0.05,
    num_leaves: int = 63,
) -> Dict[str, Any]:
    """
    Full training & evaluation execution:
    1. Chronological time-split (earlier 80% train, latest 20% validation)
    2. LightGBM training with scale_pos_weight
    3. Decision threshold tuning sweep
    4. Validation metric computation (AUC-PR, ROC-AUC, Precision, Recall, F1, Confusion Matrix)
    5. Top 20 feature importances extraction
    6. Model and metrics persistence
    """
    # 1. Split data
    X_train, y_train, X_val, y_val, feature_cols, imbalance_ratio = load_and_split_data(
        data_path=data_path,
        val_ratio=val_ratio,
    )

    # 2. Train LightGBM model
    model = train_lightgbm(
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        scale_pos_weight=imbalance_ratio,
        n_estimators=n_estimators,
        learning_rate=learning_rate,
        num_leaves=num_leaves,
    )

    # 3. Predict on Validation Split
    print("\n[*] Generating predictions on held-out validation set...")
    y_proba_val = model.predict_proba(X_val)[:, 1]

    # Calculate global ranking metrics
    auc_pr = average_precision_score(y_val, y_proba_val)
    roc_auc = roc_auc_score(y_val, y_proba_val)

    # 4. Tune threshold
    optimal_thresh, sweep_results, opt_stats = tune_threshold(
        y_true=y_val.values,
        y_proba=y_proba_val,
    )

    # 5. Extract top 20 features
    top_features = extract_top_features(model, feature_cols, top_n=20)

    # 6. Format metrics payload matching API DTO
    metrics_payload = {
        "model_name": "LightGBM Fraud Classifier",
        "model_version": "v1.0.0-trained",
        "imbalance_handling": f"scale_pos_weight ({imbalance_ratio:.2f})",
        "evaluation_dataset": f"IEEE-CIS Time-Based Validation Split (Last {val_ratio*100:.0f}%)",
        "precision": opt_stats["precision"],
        "recall": opt_stats["recall"],
        "f1_score": opt_stats["f1_score"],
        "auc_pr": round(float(auc_pr), 4),
        "roc_auc": round(float(roc_auc), 4),
        "optimal_threshold": round(float(optimal_thresh), 2),
        "confusion_matrix": {
            "true_negatives": opt_stats["true_negatives"],
            "false_positives": opt_stats["false_positives"],
            "false_negatives": opt_stats["false_negatives"],
            "true_positives": opt_stats["true_positives"],
        },
        "top_features": top_features,
        "threshold_sweep": sweep_results,
        "evaluated_at": datetime.utcnow().isoformat() + "Z",
    }

    # 7. Save model and metrics
    save_model_and_metrics(
        model=model,
        metrics_data=metrics_payload,
        model_path=model_path,
        metrics_path=metrics_path,
    )

    # 8. Print Executive Summary Report
    print("\n" + "=" * 80)
    print("                    MODEL TRAINING & EVALUATION REPORT")
    print("=" * 80)
    print(f"  Model Architecture:    LightGBM Gradient Boosted Decision Trees")
    print(f"  Training Split Size:   {len(X_train):,} samples (first {(1-val_ratio)*100:.0f}%)")
    print(f"  Validation Split Size: {len(X_val):,} samples (held-out {val_ratio*100:.0f}%)")
    print(f"  Class Imbalance Scale: {imbalance_ratio:.2f} : 1")
    print(f"--------------------------------------------------------------------------------")
    print(f"  AUC-PR (Primary Metric): {(auc_pr * 100):.2f}%")
    print(f"  ROC-AUC:                 {(roc_auc * 100):.2f}%")
    print(f"  Optimal Threshold:       {optimal_thresh:.2f}")
    print(f"  Precision @ Threshold:   {(opt_stats['precision'] * 100):.2f}%")
    print(f"  Recall @ Threshold:      {(opt_stats['recall'] * 100):.2f}%")
    print(f"  F1-Score @ Threshold:    {(opt_stats['f1_score'] * 100):.2f}%")
    print(f"--------------------------------------------------------------------------------")
    print(f"  Confusion Matrix on Validation Set ({len(X_val):,} transactions):")
    print(f"    - True Negatives (Legitimate Approved):   {opt_stats['true_negatives']:,}")
    print(f"    - False Positives (Legitimate Flagged):   {opt_stats['false_positives']:,}")
    print(f"    - False Negatives (Missed Fraud):         {opt_stats['false_negatives']:,}")
    print(f"    - True Positives (Fraud Caught):          {opt_stats['true_positives']:,}")
    print(f"--------------------------------------------------------------------------------")
    print("  Top 20 Most Important Features (by Information Gain):")
    for item in top_features:
        print(f"    {item['rank']:>2}. {item['feature']:<25} [Gain: {item['importance_gain']:>12,.1f} | {item['importance_percentage']:>5.2f}%]")
    print("=" * 80 + "\n")

    return metrics_payload


if __name__ == "__main__":
    run_training_pipeline()
