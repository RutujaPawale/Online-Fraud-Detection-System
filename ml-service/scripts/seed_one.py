"""
Single On-Demand Transaction Seeding Script.
Allows constructing a single transaction on demand (or using calibrated trigger presets)
and submits it to the api-service endpoint, printing the live decision and risk factors.

Usage:
    python scripts/seed_one.py --amount 25.00 --card-class debit
    python scripts/seed_one.py --trigger BLOCK
    python scripts/seed_one.py --trigger APPROVE
    python scripts/seed_one.py --trigger REVIEW
    python scripts/seed_one.py --amount 1250.00 --card-type mastercard --card-class credit --email-domain protonmail.com
"""

import argparse
import sys
import json
from pathlib import Path

# Add script directory to sys.path to allow imports when executed from anywhere
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ingest_helper import build_custom_payload, send_transaction, DEFAULT_API_URL


def main():
    parser = argparse.ArgumentParser(description="Submit a single custom transaction to api-service for on-demand scoring.")
    parser.add_argument("--amount", type=float, default=None, help="Transaction amount in USD (default: 75.00 or preset)")
    parser.add_argument("--card-type", type=str, default="visa", choices=["visa", "mastercard", "discover", "american express"], help="Card network (card4)")
    parser.add_argument("--card-class", type=str, default=None, choices=["debit", "credit"], help="Card category (card6)")
    parser.add_argument("--product-code", type=str, default="W", help="Product code (ProductCD: W, C, H, R, S)")
    parser.add_argument("--email-domain", type=str, default=None, help="Purchaser email domain (P_emaildomain)")
    parser.add_argument("--r-email-domain", type=str, default=None, help="Recipient email domain (R_emaildomain)")
    parser.add_argument("--device-type", type=str, default=None, choices=["desktop", "mobile"], help="Device type (DeviceType)")
    parser.add_argument("--device-info", type=str, default=None, help="Device info string (DeviceInfo)")
    parser.add_argument("--card1", type=str, default="13926", help="Card issuer ID (card1)")
    parser.add_argument("--ref", type=str, default=None, help="Custom transaction reference (default: generated unique ref)")
    parser.add_argument("--trigger", type=str, default=None, choices=["BLOCK", "APPROVE", "REVIEW"], help="Preset pattern designed to hit a specific risk tier")
    parser.add_argument("--api-url", type=str, default=DEFAULT_API_URL, help=f"API endpoint URL (default: {DEFAULT_API_URL})")

    args = parser.parse_args()

    # Base defaults
    amount = args.amount if args.amount is not None else 75.00
    card_class = args.card_class if args.card_class is not None else "debit"
    p_email = args.email_domain if args.email_domain is not None else "gmail.com"
    r_email = args.r_email_domain
    device_type = args.device_type if args.device_type is not None else "desktop"
    device_info = args.device_info if args.device_info is not None else "Windows"
    add_feats = {}

    # Apply trigger presets if specified (unless explicitly overridden by user)
    if args.trigger == "BLOCK":
        amount = args.amount if args.amount is not None else 920.00
        card_class = args.card_class if args.card_class is not None else "credit"
        p_email = args.email_domain if args.email_domain is not None else "mailinator.com"
        r_email = args.r_email_domain if args.r_email_domain is not None else "mailinator.com"
        device_type = args.device_type if args.device_type is not None else "mobile"
        device_info = args.device_info if args.device_info is not None else "Linux"
        add_feats = {
            "V258": 3.0,
            "C13": 55.0,
            "V294": 5.0,
            "C4": 12.0,
            "C1": 18.0
        }
    elif args.trigger == "APPROVE":
        amount = args.amount if args.amount is not None else 28.50
        card_class = args.card_class if args.card_class is not None else "debit"
        p_email = args.email_domain if args.email_domain is not None else "gmail.com"
        device_type = args.device_type if args.device_type is not None else "desktop"
        device_info = args.device_info if args.device_info is not None else "Windows"
        add_feats = {
            "V258": 0.0,
            "C13": 1.0,
            "V294": 0.0,
            "C4": 0.0,
            "C1": 1.0
        }
    elif args.trigger == "REVIEW":
        amount = args.amount if args.amount is not None else 260.00
        card_class = args.card_class if args.card_class is not None else "credit"
        p_email = args.email_domain if args.email_domain is not None else "yahoo.com"
        add_feats = {
            "V258": 1.0,
            "C13": 8.0,
            "V294": 1.0,
            "C4": 2.0,
            "C1": 4.0
        }

    payload = build_custom_payload(
        amount=amount,
        card_type=args.card_type,
        card_class=card_class,
        product_code=args.product_code,
        p_email=p_email,
        r_email=r_email,
        device_type=device_type,
        device_info=device_info,
        card1=args.card1,
        additional_features=add_feats,
        ref=args.ref
    )

    print("\n" + "=" * 80)
    print(f"       Submitting On-Demand Transaction -> api-service")
    if args.trigger:
        print(f"       [Preset Trigger: {args.trigger}]")
    print("=" * 80)
    print(f"[*] Target Endpoint : {args.api_url}")
    print(f"[*] Reference       : {payload['transactionRef']}")
    print(f"[*] Amount          : ${payload['amount']:,.2f} {payload.get('currency', 'USD')}")
    print(f"[*] Card Profile    : {payload.get('card4')} ({payload.get('card6')}) | Card1: {payload.get('card1')}")
    print(f"[*] Identity        : Purchaser: {payload.get('pEmailDomain', 'N/A')} | Device: {payload.get('deviceType', 'N/A')} ({payload.get('deviceInfo', 'N/A')})")

    success, code, resp_data, err_msg = send_transaction(payload, api_url=args.api_url)

    if not success:
        print(f"\n[!] Submission failed (HTTP {code}): {err_msg}")
        sys.exit(1)

    # Display live result
    decision = resp_data.get("status", "UNKNOWN")
    prob = resp_data.get("fraudProbability", 0.0)
    risk_level = resp_data.get("riskLevel", "UNKNOWN")
    model_version = resp_data.get("modelVersion", "N/A")
    tx_uuid = resp_data.get("id", "N/A")
    review_case_id = resp_data.get("reviewCaseId")

    print("\n" + "-" * 80)
    print(f"                          Scoring Result")
    print("-" * 80)
    print(f"  Decision          : {decision}")
    print(f"  Risk Tier         : {risk_level}")
    print(f"  Fraud Probability : {prob:.4f} ({prob * 100:.2f}%)")
    print(f"  Model Version     : {model_version}")
    print(f"  Transaction UUID  : {tx_uuid}")

    if review_case_id:
        print(f"  Human Review Case : {review_case_id} (Status: {resp_data.get('reviewStatus', 'PENDING')})")

    # Risk Factors Explanation
    raw_factors = resp_data.get("riskFactorsJson")
    if raw_factors:
        try:
            factors_list = json.loads(raw_factors) if isinstance(raw_factors, str) else raw_factors
            if factors_list:
                print("\n  Top Contributing Risk Factors:")
                for idx, factor in enumerate(factors_list, 1):
                    feature_name = factor.get("feature", "feature")
                    contribution = factor.get("contribution", 0.0)
                    desc = factor.get("description", "")
                    print(f"    {idx}. [{feature_name}] (+{contribution:.3f}) - {desc}")
        except Exception:
            pass

    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
