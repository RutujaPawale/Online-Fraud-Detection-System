"""
Batch Transaction Ingestion Script.
Randomly samples N transactions from the validation set (with optional seed for reproducibility),
generates unique transaction references (or supports fixed references for idempotency testing),
and submits them to the Spring Boot api-service endpoint.

Usage:
    python scripts/ingest_batch.py --count 26
    python scripts/ingest_batch.py --count 50 --seed 42
    python scripts/ingest_batch.py --fixed-ref  # Test idempotent upserts on exact IDs
"""

import argparse
import sys
from pathlib import Path

# Add script directory to sys.path to allow imports when executed from anywhere
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ingest_helper import load_validation_data, row_to_payload, send_transaction, DEFAULT_API_URL


def main():
    parser = argparse.ArgumentParser(description="Batch ingest randomly sampled validation transactions into api-service.")
    parser.add_argument("--count", type=int, default=26, help="Number of transactions to sample and ingest (default: 26)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible sampling (e.g. 42)")
    parser.add_argument("--fixed-ref", action="store_true", help="Use exact TX-{TransactionID} without unique run suffix to test idempotent updates")
    parser.add_argument("--api-url", type=str, default=DEFAULT_API_URL, help=f"API endpoint URL (default: {DEFAULT_API_URL})")

    args = parser.parse_args()

    print("\n" + "=" * 90)
    print(f"       Batch Ingestion: {args.count} Validation Transactions -> api-service")
    if args.seed is not None:
        print(f"       [Reproducible Run - Seed: {args.seed}]")
    if args.fixed_ref:
        print("       [Mode: Fixed Reference / Idempotent Upsert]")
    print("=" * 90)

    val_df = load_validation_data()
    print(f"[*] Validation pool available: {len(val_df):,} transactions.")

    sample_size = min(args.count, len(val_df))
    if args.seed is not None:
        sampled_rows = val_df.sample(n=sample_size, random_state=args.seed).reset_index(drop=True)
    else:
        sampled_rows = val_df.sample(n=sample_size).reset_index(drop=True)

    print(f"[*] Ingesting {len(sampled_rows)} transactions to {args.api_url}...\n")

    results = []
    unique_ref = not args.fixed_ref

    for i, (_, row) in enumerate(sampled_rows.iterrows(), 1):
        payload = row_to_payload(row, index=i, unique_ref=unique_ref)
        success, code, resp_data, err_msg = send_transaction(payload, api_url=args.api_url)

        if success:
            status = resp_data.get("status", "UNKNOWN")
            prob = resp_data.get("fraudProbability", 0.0)
            amount = resp_data.get("amount", payload["amount"])
            ref = resp_data.get("transactionRef", payload["transactionRef"])

            results.append({
                "ref": ref,
                "amount": amount,
                "status": status,
                "prob": prob,
                "risk_level": resp_data.get("riskLevel", "")
            })
            print(f"[{i:02d}/{sample_size:02d}] Ref: {ref:<22} | Amt: ${amount:8,.2f} | Status: {status:<8} | Prob: {prob:.4f}")
        else:
            print(f"[{i:02d}/{sample_size:02d}] Ref: {payload['transactionRef']} | FAILED (HTTP {code}): {err_msg}")

    print("\n" + "=" * 90)
    print("                         Batch Ingestion Summary")
    print("=" * 90)

    total = len(results)
    print(f"Total Transactions Successfully Ingested: {total}/{sample_size}")

    if total > 0:
        status_counts = {}
        for r in results:
            s = r["status"]
            status_counts[s] = status_counts.get(s, 0) + 1

        for status, count in sorted(status_counts.items()):
            pct = (count / total) * 100
            print(f"  * {status:<10}: {count:2d} ({pct:5.1f}%)")
    print("=" * 90)


if __name__ == "__main__":
    main()
