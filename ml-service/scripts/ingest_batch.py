"""
Batch Transaction Ingestion Script.
Selects ~26 representative transactions from the held-out validation set
(balanced across APPROVE, REVIEW/FLAGGED, and BLOCK tiers) and submits them
through api-service's transaction ingestion endpoint (POST /api/v1/transactions).

Usage:
    python scripts/ingest_batch.py
"""

import sys
import json
from pathlib import Path
import urllib.request
import urllib.error
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PARQUET_PATH = PROJECT_ROOT / "data" / "processed" / "train_merged.parquet"
API_URL = "http://localhost:8080/api/v1/transactions"


def main():
    print("\n" + "=" * 90)
    print("       Batch Ingestion: Real Validation Transactions -> api-service")
    print("=" * 90)

    if not PARQUET_PATH.exists():
        print(f"[!] Parquet file not found at: {PARQUET_PATH}")
        sys.exit(1)

    print(f"[*] Reading validation dataset from {PARQUET_PATH.name}...")
    df = pd.read_parquet(PARQUET_PATH)

    # Sort chronologically by TransactionDT and extract validation slice (last 20%)
    if "TransactionDT" in df.columns:
        df = df.sort_values("TransactionDT").reset_index(drop=True)

    val_start = int(len(df) * 0.8)
    val_df = df.iloc[val_start:].copy()

    print(f"[*] Validation pool: {len(val_df):,} transactions.")

    # Target specific representative IDs spanning all three calibrated tiers:
    # 1. APPROVE tier (< 0.30): clean payments with debit cards & verified domains
    # 2. REVIEW tier (0.30 <= score < 0.85): elevated amounts, domain mismatches, high velocity
    # 3. BLOCK tier (>= 0.85): high-risk credit cards, extreme behavioral triggers, rapid attempts

    # Pre-identified candidates from dataset analysis
    target_approve_ids = [
        3459433, 3459435, 3459436, 3459437, 3459438, 
        3459440, 3459441, 3459443, 3459444, 3459446, 3459448, 3459451
    ]
    target_review_ids = [
        3459434, 3459432, 3459507, 3459510, 3459560, 
        3459578, 3459644, 3459654
    ]
    target_block_ids = [
        3459698, 3459504, 3459499, 3459663, 3459848, 3557572
    ]

    selected_ids = target_approve_ids + target_review_ids + target_block_ids
    selected_rows = val_df[val_df["TransactionID"].isin(selected_ids)]

    # If some IDs weren't found, top up from validation slice
    if len(selected_rows) < 25:
        remaining_count = 26 - len(selected_rows)
        additional = val_df[~val_df["TransactionID"].isin(selected_ids)].head(remaining_count)
        selected_rows = pd.concat([selected_rows, additional])

    print(f"[*] Selected {len(selected_rows)} representative transactions for batch ingestion.\n")

    results = []
    
    for i, (_, row) in enumerate(selected_rows.iterrows(), 1):
        tx_id = int(row["TransactionID"])
        amount = round(float(row["TransactionAmt"]), 2)
        product_cd = str(row["ProductCD"])
        card1 = str(int(row["card1"])) if pd.notnull(row.get("card1")) else "13926"
        card4 = str(row["card4"]) if pd.notnull(row.get("card4")) else "visa"
        card6 = str(row["card6"]) if pd.notnull(row.get("card6")) else "debit"
        p_email = str(row["P_emaildomain"]) if pd.notnull(row.get("P_emaildomain")) else None
        r_email = str(row["R_emaildomain"]) if pd.notnull(row.get("R_emaildomain")) else None
        device_type = str(row["DeviceType"]) if pd.notnull(row.get("DeviceType")) else None
        device_info = str(row["DeviceInfo"]) if pd.notnull(row.get("DeviceInfo")) else None

        # Collect additional raw features
        add_feats = {}
        for col in row.index:
            if col not in [
                "TransactionID", "isFraud", "TransactionDT", "TransactionAmt", "ProductCD", 
                "card1", "card2", "card3", "card4", "card5", "card6", 
                "addr1", "addr2", "dist1", "dist2", 
                "P_emaildomain", "R_emaildomain", "DeviceType", "DeviceInfo"
            ]:
                val = row[col]
                if pd.notnull(val):
                    try:
                        add_feats[col] = float(val)
                    except (ValueError, TypeError):
                        add_feats[col] = str(val)

        payload = {
            "transactionRef": f"TX-{tx_id}",
            "userId": f"USR-{1000 + (i % 50)}",
            "amount": amount,
            "currency": "USD",
            "productCd": product_cd,
            "card1": card1,
            "card4": card4,
            "card6": card6,
            "pEmailDomain": p_email,
            "rEmailDomain": r_email,
            "deviceType": device_type,
            "deviceInfo": device_info,
            "additionalFeatures": add_feats
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(API_URL, data=data_bytes, headers={"Content-Type": "application/json"})

        try:
            with urllib.request.urlopen(req) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                results.append({
                    "tx_id": resp_data.get("id"),
                    "ref": resp_data.get("transactionRef"),
                    "amount": f"${resp_data.get('amount'):,.2f}",
                    "product": resp_data.get("productCd"),
                    "card": f"{resp_data.get('card4', 'N/A')} ({resp_data.get('card6', 'N/A')})",
                    "prob": f"{resp_data.get('fraudProbability', 0.0):.4f}",
                    "status": resp_data.get("status"),
                    "risk_level": resp_data.get("riskLevel"),
                    "factors": resp_data.get("riskFactorsJson", "[]")
                })
                print(f"[{i:02d}/26] Ref: {payload['transactionRef']} | Amt: ${amount:8,.2f} | Status: {resp_data.get('status'):<8} | Prob: {resp_data.get('fraudProbability'):.4f}")
        except urllib.error.HTTPError as e:
            print(f"[{i:02d}/26] HTTP Error {e.code}: {e.read().decode('utf-8')}")
        except Exception as e:
            print(f"[{i:02d}/26] Connection error: {e}")

    print("\n" + "=" * 90)
    print("                         Batch Ingestion Summary")
    print("=" * 90)
    
    status_counts = {}
    for r in results:
        s = r["status"]
        status_counts[s] = status_counts.get(s, 0) + 1

    print(f"Total Transactions Ingested: {len(results)}")
    for status, count in status_counts.items():
        pct = (count / len(results)) * 100
        print(f"  * {status:<10}: {count:2d} ({pct:5.1f}%)")
    print("=" * 90)


if __name__ == "__main__":
    main()
