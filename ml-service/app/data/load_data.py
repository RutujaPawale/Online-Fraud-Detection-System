import os
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
import pandas as pd

# Default project paths
CURRENT_DIR = Path(__file__).resolve().parent
ML_SERVICE_ROOT = CURRENT_DIR.parents[1]
DEFAULT_DATA_DIR = ML_SERVICE_ROOT / "data"
DEFAULT_OUTPUT_FILE = DEFAULT_DATA_DIR / "processed" / "train_merged.parquet"

# Key categorical columns specified for downstream feature engineering
KEY_CATEGORICAL_COLS = [
    "ProductCD",
    "card4",
    "card6",
    "P_emaildomain",
    "R_emaildomain",
    "DeviceType",
    "DeviceInfo",
    "M1",
    "M2",
    "M3",
    "M4",
    "M5",
    "M6",
    "M7",
    "M8",
    "M9",
]


def load_raw_data(
    data_dir: Optional[Path | str] = None,
    nrows: Optional[int] = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Loads train_transaction.csv and train_identity.csv from the specified data directory.
    """
    data_path = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
    tx_file = data_path / "train_transaction.csv"
    id_file = data_path / "train_identity.csv"

    if not tx_file.exists():
        raise FileNotFoundError(f"Missing transaction file at {tx_file}")
    if not id_file.exists():
        raise FileNotFoundError(f"Missing identity file at {id_file}")

    print(f"[*] Reading {tx_file.name} ({os.path.getsize(tx_file) / (1024**2):.1f} MB)...")
    tx_df = pd.read_csv(tx_file, nrows=nrows)

    print(f"[*] Reading {id_file.name} ({os.path.getsize(id_file) / (1024**2):.1f} MB)...")
    id_df = pd.read_csv(id_file, nrows=nrows)

    return tx_df, id_df


def merge_transaction_and_identity(
    transaction_df: pd.DataFrame,
    identity_df: pd.DataFrame,
    on: str = "TransactionID",
    how: str = "left"
) -> pd.DataFrame:
    """
    Merges transaction and identity dataframes using a left join on TransactionID.
    (Identity records are optional for transactions).
    """
    print(f"[*] Merging datasets on '{on}' using '{how}' join...")
    print(f"    - Transaction shape: {transaction_df.shape}")
    print(f"    - Identity shape:    {identity_df.shape}")

    merged_df = pd.merge(transaction_df, identity_df, on=on, how=how)
    print(f"[+] Merged dataframe shape: {merged_df.shape}")
    return merged_df


def explore_dataset(
    df: pd.DataFrame,
    target_col: str = "isFraud",
    key_categorical_cols: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Computes and prints comprehensive exploratory statistics:
    1. Shape & Memory usage
    2. Target class balance & imbalance ratio
    3. Missing value percentages (sorted descending)
    4. Dtypes breakdown (numeric vs categorical)
    5. Cardinality & missing stats for key categorical features
    """
    if key_categorical_cols is None:
        key_categorical_cols = KEY_CATEGORICAL_COLS

    results: Dict[str, Any] = {}

    print("\n" + "=" * 80)
    print("                IEEE-CIS FRAUD DETECTION DATASET EXPLORATION")
    print("=" * 80)

    # 1. Shape & Memory
    rows, cols = df.shape
    mem_mb = df.memory_usage(deep=True).sum() / (1024 ** 2)
    results["shape"] = (rows, cols)
    results["memory_mb"] = mem_mb

    print(f"\n--- 1. Dataframe Dimensions & Memory ---")
    print(f"  Rows:    {rows:,}")
    print(f"  Columns: {cols:,}")
    print(f"  Memory:  {mem_mb:.2f} MB")

    # 2. Target Class Balance
    if target_col in df.columns:
        counts = df[target_col].value_counts(dropna=False)
        percentages = df[target_col].value_counts(normalize=True, dropna=False) * 100
        n_legit = counts.get(0, 0)
        n_fraud = counts.get(1, 0)
        imbalance_ratio = (n_legit / n_fraud) if n_fraud > 0 else float("inf")

        results["class_balance"] = {
            "legit_count": int(n_legit),
            "fraud_count": int(n_fraud),
            "fraud_percentage": float(percentages.get(1, 0)),
            "imbalance_ratio": float(imbalance_ratio),
        }

        print(f"\n--- 2. Class Balance Target ('{target_col}') ---")
        print(f"  Legitimate (0): {n_legit:,} ({percentages.get(0, 0):.3f}%)")
        print(f"  Fraudulent (1): {n_fraud:,} ({percentages.get(1, 0):.3f}%)")
        print(f"  Imbalance Ratio: {imbalance_ratio:.2f} : 1  (~{percentages.get(1, 0):.2f}% positive)")
        if percentages.get(1, 0) < 5.0:
            print("  [!] Confirmed severe class imbalance (< 5% fraud). Accuracy is non-viable;")
            print("      Precision, Recall, AUC-PR, and F1-score must be used.")
    else:
        print(f"\n--- 2. Target '{target_col}' not found in dataframe. ---")

    # 3. Missing Values Summary
    missing_counts = df.isnull().sum()
    missing_pct = (missing_counts / rows) * 100
    missing_summary = pd.DataFrame({
        "missing_count": missing_counts,
        "missing_pct": missing_pct
    }).sort_values(by="missing_pct", ascending=False)

    results["missing_summary"] = missing_summary

    cols_total = len(df.columns)
    cols_with_missing = (missing_counts > 0).sum()
    cols_gt_80 = (missing_pct > 80).sum()
    cols_gt_50 = (missing_pct > 50).sum()
    cols_gt_20 = (missing_pct > 20).sum()
    cols_complete = (missing_counts == 0).sum()

    print(f"\n--- 3. Missing Value Distribution ---")
    print(f"  Columns with missing values: {cols_with_missing} / {cols_total} ({cols_with_missing/cols_total*100:.1f}%)")
    print(f"  Columns with > 80% missing:  {cols_gt_80}")
    print(f"  Columns with > 50% missing:  {cols_gt_50}")
    print(f"  Columns with > 20% missing:  {cols_gt_20}")
    print(f"  Complete columns (0% null):  {cols_complete}")

    print("\n  Top 15 Columns by Missing Percentage:")
    top_missing = missing_summary.head(15)
    for col, row_data in top_missing.iterrows():
        print(f"    - {col:<20} {int(row_data['missing_count']):>8,} nulls ({row_data['missing_pct']:>6.2f}%)")

    # 4. Dtypes Summary
    dtypes_counts = df.dtypes.value_counts()
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    results["dtypes"] = {
        "breakdown": {str(k): int(v) for k, v in dtypes_counts.items()},
        "numeric_count": len(numeric_cols),
        "categorical_count": len(categorical_cols),
    }

    print(f"\n--- 4. Column Data Types Breakdown ---")
    for dtype_name, count in dtypes_counts.items():
        print(f"  - {str(dtype_name):<12} {count:>4} columns")
    print(f"  Total Numeric:     {len(numeric_cols)} columns")
    print(f"  Total Categorical: {len(categorical_cols)} columns (object/category)")

    # 5. Key Categorical Columns Inspection
    print(f"\n--- 5. Key Categorical Columns Inspection ---")
    key_cat_records = []
    for col in key_categorical_cols:
        if col in df.columns:
            n_unique = df[col].nunique(dropna=True)
            null_pct = df[col].isnull().mean() * 100
            dtype = str(df[col].dtype)
            top_vals = df[col].value_counts(dropna=True).head(3).to_dict()
            top_vals_str = ", ".join([f"{k}: {v:,}" for k, v in top_vals.items()])
            key_cat_records.append({
                "Column": col,
                "Dtype": dtype,
                "Unique": n_unique,
                "Missing %": f"{null_pct:.1f}%",
                "Top Values": top_vals_str
            })
            print(f"  * {col:<15} [dtype: {dtype:<6} | unique: {n_unique:>5} | nulls: {null_pct:>5.1f}%]")
            if top_vals:
                print(f"      Top categories: {top_vals_str}")
        else:
            print(f"  * {col:<15} [NOT PRESENT in dataset]")

    results["key_categoricals"] = key_cat_records

    print("=" * 80 + "\n")
    return results


def save_processed_data(
    df: pd.DataFrame,
    output_path: Optional[Path | str] = None
) -> Path:
    """
    Saves the merged dataframe to a Parquet file using pyarrow.
    """
    out_file = Path(output_path) if output_path else DEFAULT_OUTPUT_FILE
    out_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"[*] Saving merged dataframe to {out_file}...")
    df.to_parquet(out_file, engine="pyarrow", index=False)
    size_mb = os.path.getsize(out_file) / (1024 ** 2)
    print(f"[+] Saved successfully! File size: {size_mb:.2f} MB")
    return out_file


def load_and_process_train(
    data_dir: Optional[Path | str] = None,
    output_path: Optional[Path | str] = None,
    explore: bool = True,
    nrows: Optional[int] = None
) -> pd.DataFrame:
    """
    End-to-end pipeline:
    1. Loads raw train_transaction.csv and train_identity.csv
    2. Left joins them on TransactionID
    3. Prints exploration diagnostics
    4. Saves to processed/train_merged.parquet
    """
    tx_df, id_df = load_raw_data(data_dir=data_dir, nrows=nrows)
    merged_df = merge_transaction_and_identity(tx_df, id_df, on="TransactionID", how="left")

    if explore:
        explore_dataset(merged_df)

    save_processed_data(merged_df, output_path=output_path)
    return merged_df


if __name__ == "__main__":
    load_and_process_train()
