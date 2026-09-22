"""
Continuous Live Transaction Streaming Simulation Script.
Submits randomly sampled transactions from the validation set every N seconds,
printing a live single-line verdict while the React dashboard updates in real time.
Handles Ctrl+C gracefully to exit cleanly.

Usage:
    python scripts/simulate_stream.py
    python scripts/simulate_stream.py --interval 2.0
    python scripts/simulate_stream.py --duration 60 --interval 3.0
"""

import argparse
import sys
import time
import signal
from datetime import datetime
from pathlib import Path

# Add script directory to sys.path to allow imports when executed from anywhere
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ingest_helper import load_validation_data, row_to_payload, send_transaction, DEFAULT_API_URL


def main():
    parser = argparse.ArgumentParser(description="Simulate real-time incoming transaction traffic into api-service.")
    parser.add_argument("--interval", type=float, default=3.0, help="Interval in seconds between transactions (default: 3.0s)")
    parser.add_argument("--duration", type=float, default=None, help="Total streaming duration in seconds (default: unlimited until Ctrl+C)")
    parser.add_argument("--seed", type=int, default=None, help="Optional random seed for sampling")
    parser.add_argument("--api-url", type=str, default=DEFAULT_API_URL, help=f"API endpoint URL (default: {DEFAULT_API_URL})")

    args = parser.parse_args()

    # Graceful stop flag
    stop_requested = False

    def handle_signal(signum, frame):
        nonlocal stop_requested
        stop_requested = True
        print("\n[!] Shutdown signal received. Finishing current submission...")

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    print("\n" + "=" * 90)
    print(f"       Simulating Real-Time Transaction Stream -> {args.api_url}")
    print(f"       [Interval: {args.interval:.1f}s | Duration: {args.duration if args.duration else 'Unlimited (Ctrl+C to stop)'}]")
    print("=" * 90)

    val_df = load_validation_data()
    print(f"[*] Validation pool: {len(val_df):,} transactions loaded.")
    print("[*] Starting transaction stream... (Press Ctrl+C to stop cleanly)\n")

    start_time = time.time()
    count = 0
    stats = {"APPROVE": 0, "FLAGGED": 0, "BLOCK": 0, "ERROR": 0}

    try:
        while not stop_requested:
            if args.duration and (time.time() - start_time) >= args.duration:
                print(f"\n[*] Target duration of {args.duration}s reached.")
                break

            count += 1
            # Sample 1 random row
            row = val_df.sample(n=1, random_state=(args.seed + count if args.seed else None)).iloc[0]
            payload = row_to_payload(row, index=count, unique_ref=True)

            success, code, resp_data, err_msg = send_transaction(payload, api_url=args.api_url)
            timestamp_str = datetime.now().strftime("%H:%M:%S")

            if success:
                status = resp_data.get("status", "UNKNOWN")
                prob = resp_data.get("fraudProbability", 0.0)
                amount = resp_data.get("amount", payload["amount"])
                ref = resp_data.get("transactionRef", payload["transactionRef"])
                risk_level = resp_data.get("riskLevel", "")

                stats[status] = stats.get(status, 0) + 1
                print(f"[{timestamp_str}] #{count:04d} | Ref: {ref:<22} | Amt: ${amount:8,.2f} | Decision: {status:<8} | Prob: {prob:.4f} | Tier: {risk_level}")
            else:
                stats["ERROR"] += 1
                print(f"[{timestamp_str}] #{count:04d} | Ref: {payload['transactionRef']} | FAILED (HTTP {code}): {err_msg}")

            # Sleep between transactions in short steps to respond promptly to Ctrl+C
            sleep_step = 0.2
            elapsed_sleep = 0.0
            while elapsed_sleep < args.interval and not stop_requested:
                time.sleep(min(sleep_step, args.interval - elapsed_sleep))
                elapsed_sleep += sleep_step

    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.")

    elapsed_total = round(time.time() - start_time, 1)
    print("\n" + "=" * 90)
    print("                       Streaming Simulation Summary")
    print("=" * 90)
    print(f"Duration Ran        : {elapsed_total} seconds")
    print(f"Total Transactions  : {count}")
    print(f"  * APPROVE         : {stats.get('APPROVE', 0)}")
    print(f"  * FLAGGED (Review): {stats.get('FLAGGED', 0)}")
    print(f"  * BLOCK           : {stats.get('BLOCK', 0)}")
    if stats.get("ERROR", 0) > 0:
        print(f"  * ERRORS          : {stats['ERROR']}")
    print("=" * 90 + "\n")


if __name__ == "__main__":
    main()
