# Data Dictionary: IEEE-CIS Fraud Detection Dataset

This reference documents the feature schemas, behavioral signals, and modeling considerations derived from the [IEEE-CIS Fraud Detection Competition](https://www.kaggle.com/c/ieee-fraud-detection).

---

## 1. Dataset Overview

The dataset is broken into two logical tables joined on `TransactionID`:
1. **`Transaction` Table**: Financial metadata, timestamps, amounts, card identifiers, and engineered behavioral aggregates.
2. **`Identity` Table**: Device attributes, IP geolocation indicators, and browser/OS fingerprints.

### Class Imbalance
- **Target Variable**: `isFraud` (Binary: `0` for legitimate, `1` for fraudulent).
- **Distribution**: Approximately **3.5%** fraud rate (~20,663 positive instances out of 590,540 rows).
- **Modeling Consequence**: **Never evaluate on Accuracy**. A naive model that predicts all negatives achieves 96.5% accuracy while missing 100% of frauds. Models must be evaluated using **AUC-PR (Area Under Precision-Recall Curve)**, **Precision at high recall**, and calibrated **F1-Score**.

---

## 2. Transaction Table Features

| Feature Name | Type | Description / Interpretation |
|---|---|---|
| `TransactionDT` | Numeric (Seconds) | Timedelta from a reference date-time. Used for transaction velocity features. |
| `TransactionAmt` | Float | Payment transaction amount in USD. Key signal for anomaly detection. |
| `ProductCD` | Categorical | Product code identifier (`W`, `C`, `R`, `H`, `S`). `C` (Credit) and `R` have higher fraud prevalence. |
| `card1` - `card6` | Categorical / Numeric | Payment card information:<br/>- `card1`: Card number hash/token<br/>- `card2`: Issuing bank<br/>- `card3`: Issuing bank country code<br/>- `card4`: Payment network (`visa`, `mastercard`, `discover`, `amex`)<br/>- `card5`: Category / tier<br/>- `card6`: Card type (`credit`, `debit`) |
| `addr1`, `addr2` | Categorical | Billing zip/region code (`addr1`) and country code (`addr2`). |
| `dist1`, `dist2` | Float | Approximate distances between billing address, postal address, and IP geolocation. |
| `P_emaildomain` | Categorical | Purchaser email domain (e.g., `gmail.com`, `yahoo.com`, `mailinator.com`). |
| `R_emaildomain` | Categorical | Recipient email domain. Mismatch between purchaser and recipient domain is a strong fraud signal. |
| `C1` - `C14` | Numeric | Counting features (e.g., how many card transactions were associated with the phone/device in a time window). |
| `D1` - `D15` | Numeric | Timedeltas (days between previous transaction, card issuance, etc.). |
| `M1` - `M9` | Categorical | Match indicators (e.g., billing name match, address match: `T`, `F`). |
| `V1` - `V339` | Numeric | Engineered Vesta behavioral and risk features. |

---

## 3. Identity Table Features

| Feature Name | Type | Description |
|---|---|---|
| `DeviceType` | Categorical | Client device form-factor (`mobile`, `desktop`, `tablet`). |
| `DeviceInfo` | Categorical | User agent / device build string (e.g., `iOS 17.4`, `Windows 11 Chrome`, `Pixel 8 Android 14`, `Trident/7.0`). |
| `id_01` - `id_11` | Numeric | Numerical identity ratings and behavioral metrics. |
| `id_12` - `id_38` | Categorical | Browser versions, operating system names, screen resolutions, proxy indicators. |

---

## 4. Imbalance Treatment Strategy

To handle the ~3.5% positive fraud distribution:
1. **Class Weighting (`scale_pos_weight`)**: In LightGBM or XGBoost, setting `scale_pos_weight = (count(negative) / count(positive)) ≈ 27.5` penalizes false negatives proportionally.
2. **SMOTE (Synthetic Minority Over-sampling Technique)**: Interpolates synthetic fraud samples within feature neighborhoods on the training fold only.
3. **Threshold Calibration**: The default 0.5 probability cutoff is uncalibrated under imbalanced loss. The system calibrates decision cutoffs based on cost matrices:
   - `< 0.30` $\rightarrow$ `APPROVE`
   - `0.30 - 0.75` $\rightarrow$ `FLAGGED` (Human Review)
   - `\ge 0.75` $\rightarrow$ `BLOCK`
