# Online Transaction Fraud Detection Platform

[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-3.3.3-brightgreen.svg)](https://spring.io/projects/spring-boot)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg)](https://fastapi.tiangolo.com)
[![LightGBM](https://img.shields.io/badge/LightGBM-4.5.0-blue.svg)](https://lightgbm.readthedocs.io)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://reactjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791.svg)](https://www.postgresql.org/)
[![AUC-PR](https://img.shields.io/badge/Validation%20AUC--PR-51.44%25-orange.svg)]()
[![ROC-AUC](https://img.shields.io/badge/Validation%20ROC--AUC-91.28%25-success.svg)]()

A production-grade, end-to-end transaction fraud detection platform designed to detect payment card fraud in real time. Built with an asynchronous microservice architecture comprising a **Java Spring Boot 3** gateway & decision orchestration engine, a high-throughput **Python FastAPI** scoring service powered by a trained **LightGBM** classifier with explainable risk contributions, a **PostgreSQL** relational audit store, and a **React 18** analyst dashboard supporting human-in-the-loop triage.

---

## 1. System Architecture

The platform operates across four decoupled components communicating over high-speed REST contracts:

```
                                  +---------------------------------------+
                                  |       React Analyst Dashboard         |
                                  |        (Port 5173 / Vite dev)         |
                                  |  - Live Ingested Feed & Filter Tabs   |
                                  |  - Real-Time KPI Cards (AUC-PR, ROC)  |
                                  |  - Human-in-the-Loop Review Modal     |
                                  +-------------------+-------------------+
                                                      |
                                                      | HTTP / JSON Proxy
                                                      v
  +-----------------------+               +-----------------------+
  | Inbound Transactions  |               |     Spring Boot 3     |
  | (Checkout Simulator / +-------------->|     (api-service)     |
  |  E-Commerce Gateway)  |  POST /txs    |      (Port 8080)      |
  +-----------------------+               +-----------+-----------+
                                                      |
                          +---------------------------+---------------------------+
                          | JDBC (HikariCP)                                       | HTTP REST
                          v                                                       v
              +-----------------------+                               +-----------------------+
              |      PostgreSQL       |                               |    Python FastAPI     |
              |       (Port 5432)     |                               |     (ml-service)      |
              | - transactions        |                               |      (Port 8000)      |
              | - fraud_assessments   |                               | - Fitted Pipeline     |
              | - review_cases        |                               | - LightGBM Inference  |
              +-----------------------+                               | - Risk Factor Mapping |
                                                                      +-----------------------+
```

### Microservice Directory Map

| Service | Technology Stack | Port | Core Responsibilities |
| :--- | :--- | :--- | :--- |
| [**`api-service`**](./api-service) | Java 21 LTS, Spring Boot 3.3.3, Spring Data JPA, PostgreSQL Driver | `8080` | High-concurrency transaction ingestion, synchronous downstream ML invocation, two-threshold decision routing (`APPROVE`, `FLAGGED`, `BLOCK`), and analyst review API. |
| [**`ml-service`**](./ml-service) | Python 3.14 / 3.11, FastAPI, LightGBM, scikit-learn, Pandas, PyArrow | `8000` | Sub-50ms inference engine loading serialized preprocessor (`models/preprocessor.joblib`) and model (`models/fraud_model.joblib`), dynamic risk factor explanations, and live evaluation benchmark endpoint (`GET /api/v1/metrics`). |
| [**`dashboard`**](./dashboard) | React 18, Vite, TypeScript, Lucide Icons | `5173` | Visual operations console featuring live transaction streaming, tabbed risk filtering (`ALL`, `FLAGGED`, `BLOCK`, `APPROVE`), 4-quadrant confusion matrix visualization, and review resolution modals. |
| [**`database`**](./database) | PostgreSQL 15 | `5432` | Relational audit store maintaining transactions, evaluated risk probabilities, and human resolution histories with pgcrypto UUID primary keys and JSONB factor storage. |

---

## 2. Problem Framing & The IEEE-CIS Dataset

Online card-not-present fraud detection is characterized by **extreme class imbalance**, **adversarial concept drift**, and **heterogeneous high-dimensional feature spaces**.

### 2.1 Dataset Profile
The system is built and benchmarked on the [IEEE-CIS Fraud Detection dataset](https://www.kaggle.com/c/ieee-fraud-detection) (jointly released by Vesta Corporation):
- **Volume**: 590,540 raw transactions across merged transaction and identity records.
- **Dimensionality**: 434 raw features spanning payment amounts, card attributes (`card1`–`card6`), geographical distances (`dist1`, `dist2`), email domain pairings (`P_emaildomain`, `R_emaildomain`), identity device types, OS fingerprints, and 339 Vesta behavioral/velocity counters (`V1`–`V339`).
- **Heavy Sparsity**: 74 columns exhibit $>80\%$ missing values (mostly optional device/identity fields where users checked out without biometric verification).

### 2.2 Feature Engineering Pipeline ([`ml-service/app/features/`](./ml-service/app/features/))
The fitted preprocessing pipeline (`preprocessor.joblib`) executes the following transformations in memory:
1. **Domain Feature Engineering**:
   - Ratio of transaction amount to historical card mean: `amt_to_card1_mean` and `amt_card1_zscore`.
   - Cyclical temporal indicators: `transaction_hour` and `transaction_day` derived from epoch delta `TransactionDT`.
   - Cross-domain mismatch flags: `email_domain_mismatch = (P_emaildomain != R_emaildomain)`.
   - Identity presence indicator: `has_identity = 1` if biometric/device metadata exists.
2. **Missingness Pruning & Indicators**:
   - Ultra-sparse raw columns ($>85\%$ missing) dropped to avoid tree overfitting.
   - Informative binary missing indicators created (`is_missing_DeviceType`, `is_missing_dist2`, etc.).
3. **Categorical & Match Flag Encoding**:
   - High-cardinality email domains binned to top 15 categories with long tails mapped to `'other'`.
   - Match flags (`M1`–`M9`) encoded into numeric state matrices ($1.0$, $0.0$, $-1.0$ for missing).
   - One-hot encoding on low-cardinality features (`ProductCD`, `card4`, `card6`).
4. **Imputation**: Vectorized median imputation on numeric features with batch-concatenated missing column alignment.

---

## 3. Class Imbalance & Evaluation Strategy

### 3.1 Imbalance Ratio: 27.58 to 1
Out of 590,540 transactions, only **20,663 are fraudulent (3.499%)**. 
- A trivial model predicting "legitimate" on every transaction achieves **96.50% Accuracy** while catching **0% of fraud attacks**.
- **Accuracy is actively deceptive** in fraud detection and is entirely discarded.

### 3.2 Chronological Validation Split (No Random K-Fold)
In production fraud detection, past transactions are used to predict *future* fraud attacks. Fraudsters constantly innovate new patterns (device spoofing, bot nets, credential stuffing).
- Random K-Fold cross-validation leaks future behavioral signals into past training data, yielding unrealistically optimistic metrics that collapse in production.
- We implement a **strict chronological time-based split** on `TransactionDT`:
  - **Training Set (Earliest 80%)**: 472,432 transactions.
  - **Validation Set (Most Recent 20%)**: 118,108 held-out transactions.

### 3.3 Class Weighting vs. SMOTE
Rather than synthesizing artificial minority examples with SMOTE (which generates synthetic points that distort high-dimensional discrete card/device spaces and increases memory overhead by orders of magnitude):
- We utilize LightGBM's native **`scale_pos_weight = 27.46`** (computed as $\frac{N_{\text{neg}}}{N_{\text{pos}}}$).
- This multiplies gradients for minority fraud instances during tree boosting, forcing the loss function to heavily penalize false negatives while preserving true empirical feature distributions and sub-5-minute training times.

---

## 4. Model Evaluation & Benchmark Results

The model was evaluated on the **118,108 held-out transactions** from the most recent 20% validation split.

### 4.1 Primary North Star: AUC-PR
Because standard ROC-AUC evaluates true positive rate against false positive rate (which is heavily buffered by 114,044 true negatives), **AUC-PR (Area Under the Precision-Recall Curve)** is our primary optimization metric.

| Metric | Score | Significance |
| :--- | :--- | :--- |
| **AUC-PR** | **51.44%** | **~15x lift** over the uninformative random baseline of $3.44\%$. |
| **ROC-AUC** | **91.28%** | Exceptional discriminative power separating fraud and non-fraud distributions. |
| **Precision @ 0.85** | **62.90%** | Out of every 10 transactions automatically blocked, >6 are confirmed fraud attacks. |
| **Recall @ 0.85** | **40.92%** | Catches 1,663 confirmed attacks completely autonomously with zero analyst friction. |
| **F1 Score** | **49.58%** | Peak harmonic balance achieved at calibrated threshold $t = 0.85$. |

### 4.2 Test Set Confusion Matrix (at Optimal Threshold $t = 0.85$)
Evaluated across all 118,108 held-out validation transactions:

```
                            PREDICTED CLASS
                      Legitimate          Fraud
ACTUAL  Legitimate  TN = 113,063      FP = 981
CLASS   Fraud       FN =   2,401      TP = 1,663
```
- **False Alarm Rate**: $\frac{981}{113,063 + 981} = \mathbf{0.86\%}$ (less than 1 legitimate customer in 100 encounters friction).

### 4.3 Top 5 Predictive Features by Information Gain
1. **`V258` (13.52% gain)**: Vesta proprietary behavioral payment velocity trigger.
2. **`C13` (7.59% gain)**: Cumulative transaction frequency associated with card account.
3. **`V294` (6.73% gain)**: Cumulative counter measuring rapid velocity anomalies.
4. **`C4` (3.32% gain)**: Card network repeated attempt count.
5. **`card1` / `C1` (~2.96% gain each)**: Cardholder identity profile and account counter.

---

## 5. Decision Engine Design & Two-Threshold Policy

In financial risk management, the cost of a False Negative (chargeback fee + lost merchandise + card brand fines, often $\$150 - \$500+$) is substantially higher than the cost of human review ($\$2 - \$5$ analyst triage).

To balance automated speed against risk exposure, we enforce a **calibrated two-threshold decision scheme**:

```
Fraud Probability Score (0.0000 -----------------------------------------------------> 1.0000)
[     APPROVE (< 0.30)     ] [        REVIEW (0.30 <= p < 0.85)       ] [     BLOCK (>= 0.85)     ]
  Zero-friction checkout       Flagged for human analyst investigation     Immediate rejection
  Recall priority baseline     Captures 85.5% of all fraud attacks         Peak precision (62.9%)
```

### Policy Rationale
1. **`APPROVE` ($p < 0.30$)**:
   - Represents $>50\%$ of typical validation volume.
   - Lowest friction; instant payment clearance for low-risk, verified cardholders.
2. **`REVIEW` ($0.30 \le p < 0.85$)**:
   - Sweeping threshold at $t = 0.30$ achieves **85.51% Recall** (capturing 3,475 out of 4,064 validation frauds).
   - Suspicious, ambiguous transactions are not hard-blocked (which risks alienating good customers); instead, they are routed to `review_cases` for human inspection.
3. **`BLOCK` ($p \ge 0.85$)**:
   - Threshold calibrated to the peak F1 score ($49.58\%$).
   - Minimizes false declines (Precision $62.90\%$).
   - High-velocity card attacks and extreme velocity bursts are stopped immediately without human delay.

---

## 6. Analyst Review Workflow

Flagged transactions undergo human-in-the-loop investigation:

```
[ Inbound Transaction ] 
          |
    (Score: 0.7742)
          v
[ Status: FLAGGED ] ----> Persisted to PostgreSQL (status='FLAGGED', review_status='PENDING')
                                      |
                                      v
                      Dashboard [Review Case] Clicked
                                      |
                       TransactionDetailsModal Opens
                       - Inspect Features & Deviations
                       - Review Model Explanations (V258, C4, Amt)
                       - Enter Analyst Notes
                                      |
             +------------------------+------------------------+
             |                                                 |
[ Confirm Fraud (Block) ]                             [ False Positive (Approve) ]
             |                                                 |
PATCH /api/v1/reviews/{id}                         PATCH /api/v1/reviews/{id}
status -> BLOCK                                    status -> APPROVE
review_status -> CONFIRMED_FRAUD                   review_status -> FALSE_POSITIVE
resolved_at -> CURRENT_TIMESTAMP                   resolved_at -> CURRENT_TIMESTAMP
```

---

## 7. Setup & Execution Instructions

### Option A: Complete Stack via Docker Compose (Recommended)
Launch PostgreSQL, the Python ML Service, the Java Spring Boot API Gateway, and the React Dashboard together:
```bash
docker-compose up --build
```
- **Dashboard UI**: [http://localhost:5173](http://localhost:5173)
- **API Service Gateway**: [http://localhost:8080](http://localhost:8080)
- **ML Service OpenAPI Docs**: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)

### Option B: Native User-Space Execution

#### 1. PostgreSQL Database
```powershell
# Start local/portable PostgreSQL on port 5432
pg_ctl -D "C:\Users\rutuj\tools\pgsql\data" start
# Apply initial schema
psql -h 127.0.0.1 -p 5432 -U postgres -d fraud_detection_db -f "database/init.sql"
```

#### 2. ML Service (FastAPI)
```powershell
cd ml-service
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

#### 3. API Service (Spring Boot)
```powershell
cd api-service
$env:JAVA_HOME = "C:\Users\rutuj\tools\jdk-21.0.4+7"
& "C:\Users\rutuj\tools\apache-maven-3.9.8\bin\mvn.cmd" spring-boot:run
```

#### 4. React Dashboard
```powershell
cd dashboard
npm run dev -- --port 5173
```

#### 5. Seed Representative Validation Transactions
Submit a batch of 26 curated validation transactions (spanning APPROVE, REVIEW, and BLOCK tiers):
```powershell
cd ml-service
python scripts/ingest_batch.py
```

---

## 8. Engineering Limitations

1. **Cold-Start Card Profiling**:
   - Aggregation features like `amt_to_card1_mean` rely on historical cardholder behavior. First-time cards lack transaction baselines and must fall back to global population medians, slightly degrading initial precision.
2. **Synchronous In-Memory Lookups**:
   - In the current architecture, feature engineering occurs synchronously inside `ml-service` per request. At scale ($10,000+\text{ TPS}$), calculating rolling card velocity across historical time-windows requires a dedicated distributed cache or feature store.
3. **Identity Table Sparsity**:
   - $76\%$ of transactions in the IEEE-CIS benchmark dataset do not contain identity rows (reflecting guest checkouts). While missingness indicators (`is_missing_DeviceType`) extract signal, device-based fraud rules are constrained when device fingerprints are absent.
4. **Offline Batch Preprocessor**:
   - Rare categorical values outside the top 15 domains are binned into `'other'`. Novel fraudulent email providers (e.g., disposable domain generators) will be grouped into `'other'` until periodic feature pipeline refitting.

---

## 9. Future Work & Production Roadmap

- [ ] **Real-Time Streaming Ingestion (Kafka / Redpanda)**:
  Decouple transaction ingestion from scoring with an event-driven architecture using Kafka partitions keyed by `card1`, ensuring ordered streaming calculations.
- [ ] **Online Feature Store (Feast / Redis)**:
  Maintain sliding time-window features (e.g., number of attempts in last 5 minutes, 1 hour, 24 hours) computed by Apache Flink or Redis cell-rate limiters for sub-5ms feature lookups.
- [ ] **Automated Retraining & Champion-Challenger Pipelines**:
  Implement automated Airflow / Kubeflow pipelines triggered on schedule or performance degradation to retrain LightGBM models on newly resolved review verdicts.
- [ ] **Data Drift & Concept Drift Monitoring (Evidently AI / WhyLogs)**:
  Track Kolmogorov-Smirnov statistics and Population Stability Index (PSI) on top predictive features (`V258`, `C13`, `C4`) and monitor prediction score calibration against confirmed chargeback outcomes.
- [ ] **Shadow Deployments / Canary Scoring**:
  Run new candidate models in shadow mode inside `ml-service`, logging predictions asynchronously without influencing live routing until statistical parity is proven.

---

## 10. License & Acknowledgements
- **Dataset**: IEEE Computational Intelligence Society (IEEE-CIS) & Vesta Corporation.
- **License**: Apache 2.0. Built for educational and portfolio demonstration.
