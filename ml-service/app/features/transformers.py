import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from sklearn.base import BaseEstimator, TransformerMixin


class FraudDomainFeatureEngineer(BaseEstimator, TransformerMixin):
    """
    Engineers high-signal domain features for transaction fraud detection:
    - Transaction amount ratio & z-score relative to card1 group
    - Time-since-last-transaction delta per card1
    - Cyclical hour-of-day & day-of-week from TransactionDT
    - Email domain mismatch flag (purchaser vs recipient)
    - Identity record presence indicator
    """

    def __init__(self):
        self.card1_stats_: Dict[str, Tuple[float, float]] = {}
        self.global_amt_mean_: float = 135.0
        self.global_amt_std_: float = 230.0
        self.global_time_delta_median_: float = 86400.0

    def fit(self, X: pd.DataFrame, y=None):
        df = X if isinstance(X, pd.DataFrame) else pd.DataFrame(X)

        if "TransactionAmt" in df.columns:
            self.global_amt_mean_ = float(df["TransactionAmt"].mean())
            self.global_amt_std_ = float(df["TransactionAmt"].std())
            if np.isnan(self.global_amt_std_) or self.global_amt_std_ == 0:
                self.global_amt_std_ = 1.0

        if "card1" in df.columns and "TransactionAmt" in df.columns:
            grouped = df.groupby("card1")["TransactionAmt"].agg(["mean", "std"])
            for card, row in grouped.iterrows():
                m = float(row["mean"]) if not np.isnan(row["mean"]) else self.global_amt_mean_
                s = float(row["std"]) if (not np.isnan(row["std"]) and row["std"] > 0) else self.global_amt_std_
                self.card1_stats_[str(card)] = (m, s)

        if "TransactionDT" in df.columns and "card1" in df.columns and len(df) > 1:
            # Estimate typical inter-transaction delta
            deltas = df.sort_values(["card1", "TransactionDT"]).groupby("card1")["TransactionDT"].diff().dropna()
            if len(deltas) > 0:
                self.global_time_delta_median_ = float(deltas.median())

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        df = X.copy() if isinstance(X, pd.DataFrame) else pd.DataFrame(X).copy()

        # 1. Transaction Amount relative to card1
        if "TransactionAmt" in df.columns:
            if "card1" in df.columns:
                means = []
                stds = []
                for c in df["card1"]:
                    card_key = str(c)
                    if card_key in self.card1_stats_:
                        m, s = self.card1_stats_[card_key]
                    else:
                        m, s = self.global_amt_mean_, self.global_amt_std_
                    means.append(m)
                    stds.append(s)

                means = np.array(means)
                stds = np.array(stds)
                amt = df["TransactionAmt"].values

                df["amt_to_card1_mean"] = amt / (means + 1e-5)
                df["amt_card1_zscore"] = (amt - means) / (stds + 1e-5)
            else:
                df["amt_to_card1_mean"] = df["TransactionAmt"] / (self.global_amt_mean_ + 1e-5)
                df["amt_card1_zscore"] = (df["TransactionAmt"] - self.global_amt_mean_) / (self.global_amt_std_ + 1e-5)

        if "TransactionDT" in df.columns:
            dt = pd.to_numeric(df["TransactionDT"], errors="coerce").fillna(0).to_numpy()
            df["transaction_hour"] = ((dt // 3600) % 24).astype(float)
            df["transaction_day"] = ((dt // (3600 * 24)) % 7).astype(float)

            if "card1" in df.columns and len(df) > 1:
                # Grouped diff on index order
                df["time_since_last_tx"] = df.groupby("card1")["TransactionDT"].diff().fillna(self.global_time_delta_median_)
            else:
                df["time_since_last_tx"] = self.global_time_delta_median_

        # 3. Email domain mismatch flag
        p_email = df["P_emaildomain"].fillna("") if "P_emaildomain" in df.columns else pd.Series([""] * len(df))
        r_email = df["R_emaildomain"].fillna("") if "R_emaildomain" in df.columns else pd.Series([""] * len(df))

        both_present = (p_email != "") & (r_email != "")
        mismatch = both_present & (p_email != r_email)
        df["email_domain_mismatch"] = mismatch.astype(int)
        df["has_recipient_email"] = (r_email != "").astype(int)

        # 4. Identity presence flag
        if "DeviceType" in df.columns:
            df["has_identity"] = df["DeviceType"].notnull().astype(int)
        elif "id_01" in df.columns:
            df["has_identity"] = df["id_01"].notnull().astype(int)
        else:
            df["has_identity"] = 0

        return df


class SparseMissingIndicator(BaseEstimator, TransformerMixin):
    """
    Flags informative ultra-sparse columns by generating binary is_missing_* indicators,
    and drops ultra-sparse raw columns exceeding the missingness threshold.
    """

    def __init__(
        self,
        missing_threshold: float = 0.85,
        indicator_cols: Optional[List[str]] = None
    ):
        self.missing_threshold = missing_threshold
        self.indicator_cols = indicator_cols or [
            "DeviceType", "DeviceInfo", "dist2", "D7", "D13", "D14",
            "id_01", "id_18", "id_24", "id_25"
        ]
        self.cols_to_drop_: List[str] = []
        self.active_indicators_: List[str] = []

    def fit(self, X: pd.DataFrame, y=None):
        df = X if isinstance(X, pd.DataFrame) else pd.DataFrame(X)
        n_rows = len(df)

        missing_frac = df.isnull().sum() / n_rows

        # Track which requested indicator columns exist
        self.active_indicators_ = [c for c in self.indicator_cols if c in df.columns]

        # Protected core columns that must never be dropped
        protected = {
            "isFraud", "TransactionID", "TransactionAmt", "ProductCD", "card1",
            "card4", "card6", "P_emaildomain", "R_emaildomain", "DeviceType",
            "amt_to_card1_mean", "amt_card1_zscore", "time_since_last_tx"
        }

        # Columns exceeding threshold to drop
        self.cols_to_drop_ = [
            col for col, frac in missing_frac.items()
            if frac >= self.missing_threshold and col not in protected
        ]

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        df = X.copy() if isinstance(X, pd.DataFrame) else pd.DataFrame(X).copy()

        # Add is_missing indicators for high-signal sparse features
        for col in self.active_indicators_:
            if col in df.columns:
                df[f"is_missing_{col}"] = df[col].isnull().astype(int)

        # Drop ultra-sparse raw columns
        drop_existing = [c for c in self.cols_to_drop_ if c in df.columns]
        if drop_existing:
            df = df.drop(columns=drop_existing)

        return df


class MatchFlagEncoder(BaseEstimator, TransformerMixin):
    """
    Encodes match flags M1-M9 into numeric values:
    'T' -> 1.0, 'F' -> 0.0, 'M0'->0.0, 'M1'->1.0, 'M2'->2.0, missing -> -1.0
    """

    def __init__(self):
        self.match_cols = [f"M{i}" for i in range(1, 10)]
        self.mapping = {
            "T": 1.0,
            "F": 0.0,
            "M0": 0.0,
            "M1": 1.0,
            "M2": 2.0,
        }

    def fit(self, X: pd.DataFrame, y=None):
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        df = X.copy() if isinstance(X, pd.DataFrame) else pd.DataFrame(X).copy()

        for col in self.match_cols:
            if col in df.columns:
                s = df[col].astype(str).str.strip().map(self.mapping)
                df[col] = s.fillna(-1.0).astype(float)

        return df


class EmailDomainGrouper(BaseEstimator, TransformerMixin):
    """
    Groups rare long-tail email domains into an 'other' bucket,
    and fills missing domains with 'missing'.
    """

    def __init__(self, top_n: int = 15):
        self.top_n = top_n
        self.top_p_domains_: List[str] = []
        self.top_r_domains_: List[str] = []

    def fit(self, X: pd.DataFrame, y=None):
        df = X if isinstance(X, pd.DataFrame) else pd.DataFrame(X)

        if "P_emaildomain" in df.columns:
            top_p = df["P_emaildomain"].dropna().value_counts().head(self.top_n).index.tolist()
            self.top_p_domains_ = top_p

        if "R_emaildomain" in df.columns:
            top_r = df["R_emaildomain"].dropna().value_counts().head(self.top_n).index.tolist()
            self.top_r_domains_ = top_r

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        df = X.copy() if isinstance(X, pd.DataFrame) else pd.DataFrame(X).copy()

        if "P_emaildomain" in df.columns:
            p_series = df["P_emaildomain"].fillna("missing").astype(str)
            df["P_emaildomain"] = p_series.apply(
                lambda d: d if d in self.top_p_domains_ or d == "missing" else "other"
            )

        if "R_emaildomain" in df.columns:
            r_series = df["R_emaildomain"].fillna("missing").astype(str)
            df["R_emaildomain"] = r_series.apply(
                lambda d: d if d in self.top_r_domains_ or d == "missing" else "other"
            )

        return df
