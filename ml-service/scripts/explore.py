"""
Script to execute the IEEE-CIS data loader, print exploratory analysis,
and generate the train_merged.parquet file in data/processed/.

Usage:
    python scripts/explore.py
    python scripts/explore.py --nrows 50000   # Quick test on first 50,000 rows
"""

import sys
import argparse
from pathlib import Path

# Add ml-service root to python path
ML_SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(ML_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_SERVICE_ROOT))

from app.data.load_data import load_and_process_train


def main():
    parser = argparse.ArgumentParser(description="Load, merge, and explore IEEE-CIS Fraud Detection dataset.")
    parser.add_argument(
        "--nrows",
        type=int,
        default=None,
        help="Optional number of rows to read for quick exploration testing."
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Path to data directory containing raw CSVs."
    )
    parser.add_argument(
        "--output-path",
        type=str,
        default=None,
        help="Path where the merged parquet file should be saved."
    )

    args = parser.parse_args()

    print(f"\n========================================================")
    print(f" IEEE-CIS Fraud Detection - Ingestion & Exploration Tool ")
    print(f"========================================================")
    if args.nrows:
        print(f"[!] Running in sample mode: nrows={args.nrows:,}")

    load_and_process_train(
        data_dir=args.data_dir,
        output_path=args.output_path,
        explore=True,
        nrows=args.nrows
    )

    print("\n[OK] Ingestion and exploration complete!")
    print("     Merged dataset is now saved and ready for feature engineering.\n")


if __name__ == "__main__":
    main()
