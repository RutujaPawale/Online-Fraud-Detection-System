"""
Shared ingestion and API communication helpers for the Fraud Detection System seeding utilities.
Used by:
  - ingest_batch.py
  - seed_one.py
  - simulate_stream.py
"""

import os
import sys
import json
import secrets
import time
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import urllib.request
import urllib.error
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PARQUET_PATH = PROJECT_ROOT / "data" / "processed" / "train_merged.parquet"
DEFAULT_API_URL = os.getenv("API_URL", "http://localhost:8080/api/v1/transactions")


def load_validation_data(parquet_path: Path = PARQUET_PATH, val_ratio: float = 0.2) -> pd.DataFrame:
    """Loads the validation slice (last 20% chronologically) from train_merged.parquet."""
    if not parquet_path.exists():
        print(f"[!] Dataset not found at: {parquet_path}")
        sys.exit(1)

    df = pd.read_parquet(parquet_path)
    if "TransactionDT" in df.columns:
        df = df.sort_values("TransactionDT").reset_index(drop=True)

    val_start = int(len(df) * (1.0 - val_ratio))
    val_df = df.iloc[val_start:].copy().reset_index(drop=True)
    return val_df


def row_to_payload(
    row: pd.Series,
    index: int = 1,
    unique_ref: bool = True,
    ref_suffix: Optional[str] = None
) -> Dict[str, Any]:
    """Converts a row from the validation dataframe into an api-service TransactionRequest payload."""
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

    # Collect additional numeric and categorical features
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

    if unique_ref:
        suffix = ref_suffix if ref_suffix else secrets.token_hex(2)
        ref = f"TX-{tx_id}-{suffix}"
    else:
        ref = f"TX-{tx_id}"

    payload = {
        "transactionRef": ref,
        "userId": f"USR-{1000 + (index % 100)}",
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

    return {k: v for k, v in payload.items() if v is not None}


def build_custom_payload(
    amount: float,
    card_type: str = "visa",
    card_class: str = "debit",
    product_code: str = "W",
    p_email: Optional[str] = "gmail.com",
    r_email: Optional[str] = None,
    device_type: Optional[str] = "desktop",
    device_info: Optional[str] = "Windows",
    card1: str = "13926",
    additional_features: Optional[Dict[str, Any]] = None,
    ref: Optional[str] = None
) -> Dict[str, Any]:
    """Builds a custom single transaction payload from user parameters."""
    if not ref:
        ts = int(time.time())
        token = secrets.token_hex(2)
        ref = f"TX-CUSTOM-{ts}-{token}"

    payload = {
        "transactionRef": ref,
        "userId": f"USR-{secrets.randbelow(9000) + 1000}",
        "amount": round(float(amount), 2),
        "currency": "USD",
        "productCd": product_code,
        "card1": str(card1),
        "card4": card_type,
        "card6": card_class,
        "pEmailDomain": p_email,
        "rEmailDomain": r_email,
        "deviceType": device_type,
        "deviceInfo": device_info,
        "additionalFeatures": additional_features or {}
    }
    return {k: v for k, v in payload.items() if v is not None}


def send_transaction(payload: Dict[str, Any], api_url: str = DEFAULT_API_URL) -> Tuple[bool, int, Dict[str, Any], str]:
    """
    Submits a transaction payload to the Spring Boot api-service endpoint.
    Returns: (success: bool, status_code: int, response_dict: dict, error_message: str)
    """
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        api_url,
        data=data_bytes,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_body = resp.read().decode("utf-8")
            resp_data = json.loads(resp_body) if resp_body else {}
            return True, resp.status, resp_data, ""
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace")
        return False, e.code, {}, err_msg
    except Exception as e:
        return False, 0, {}, str(e)
