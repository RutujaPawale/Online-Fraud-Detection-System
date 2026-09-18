# Inter-Service API Contracts & REST Specifications

This document defines the REST API contracts, request payloads, response structures, and HTTP status codes across the microservices.

---

## 1. `ml-service` (Python / FastAPI)

Base URL: `http://localhost:8000`

### 1.1 `POST /api/v1/score`
Computes the fraud probability score for a given transaction based on IEEE-CIS features.

**Headers**:
- `Content-Type: application/json`

**Request Body (`TransactionFeatures`)**:
```json
{
  "transaction_ref": "TX-948201",
  "transaction_amt": 389.50,
  "product_cd": "W",
  "card1": "13926",
  "card2": "321",
  "card3": "150",
  "card4": "visa",
  "card5": "226",
  "card6": "credit",
  "addr1": "315",
  "addr2": "87",
  "dist1": 19.0,
  "p_emaildomain": "gmail.com",
  "r_emaildomain": "anonymous-relay.net",
  "device_type": "mobile",
  "device_info": "iOS 17.4",
  "browser_version": "Safari 17.0"
}
```

**Response (`200 OK` - `PredictionResponse`)**:
```json
{
  "transaction_ref": "TX-948201",
  "fraud_probability": 0.5420,
  "risk_level": "MEDIUM",
  "recommendation": "FLAGGED",
  "model_version": "v0.1.0-baseline",
  "risk_factors": [
    {
      "feature": "email_domain",
      "contribution": 0.40,
      "description": "Disposable or anonymized email domain detected"
    },
    {
      "feature": "transaction_amt",
      "contribution": 0.10,
      "description": "Elevated transaction amount ($389.50)"
    }
  ],
  "evaluated_at": "2026-09-17T06:40:00.000Z"
}
```

---

### 1.2 `GET /api/v1/metrics`
Returns current model performance metrics evaluated on the test set.

**Response (`200 OK` - `ModelMetricsResponse`)**:
```json
{
  "model_name": "LightGBM Fraud Classifier",
  "model_version": "v0.1.0-baseline",
  "imbalance_handling": "Class Weighting + SMOTE",
  "evaluation_dataset": "IEEE-CIS Fraud Detection Validation Set",
  "precision": 0.884,
  "recall": 0.812,
  "f1_score": 0.846,
  "auc_pr": 0.895,
  "roc_auc": 0.942,
  "optimal_threshold": 0.45,
  "confusion_matrix": {
    "true_negatives": 110400,
    "false_positives": 420,
    "false_negatives": 680,
    "true_positives": 2980
  },
  "evaluated_at": "2026-09-17T06:00:00.000Z"
}
```

---

### 1.3 `GET /api/v1/health`
Health check probe.

**Response (`200 OK`)**:
```json
{
  "status": "healthy",
  "service": "Fraud Detection ML Service",
  "model_version": "v0.1.0-baseline",
  "is_model_loaded": true,
  "timestamp": "2026-09-17T06:40:00.000000"
}
```

---

## 2. `api-service` (Java / Spring Boot)

Base URL: `http://localhost:8080`

### 2.1 `POST /api/v1/transactions`
Ingests an incoming transaction, scores it via `ml-service`, applies decision threshold, and persists to PostgreSQL.

**Headers**:
- `Content-Type: application/json`

**Request Body (`TransactionRequest`)**:
```json
{
  "transactionRef": "TX-948201",
  "userId": "USR-8472",
  "amount": 389.50,
  "currency": "USD",
  "productCd": "W",
  "card1": "13926",
  "card4": "visa",
  "card6": "credit",
  "pEmailDomain": "gmail.com",
  "rEmailDomain": "anonymous-relay.net",
  "deviceType": "mobile",
  "deviceInfo": "iOS 17.4"
}
```

**Response (`201 Created` - `TransactionResponse`)**:
```json
{
  "id": "c76a911e-9273-4556-9a2c-b4bb13d78912",
  "transactionRef": "TX-948201",
  "userId": "USR-8472",
  "amount": 389.50,
  "currency": "USD",
  "productCd": "W",
  "card4": "visa",
  "card6": "credit",
  "pEmailDomain": "gmail.com",
  "rEmailDomain": "anonymous-relay.net",
  "deviceType": "mobile",
  "deviceInfo": "iOS 17.4",
  "status": "FLAGGED",
  "createdAt": "2026-09-17T06:40:15.123Z",
  "fraudProbability": 0.5420,
  "riskLevel": "MEDIUM",
  "modelVersion": "v0.1.0-baseline",
  "riskFactorsJson": "[{\"feature\":\"email_domain\",\"contribution\":0.4,\"description\":\"Disposable or anonymized email domain detected\"}]",
  "reviewCaseId": "18fba814-1e08-410a-ba55-920f06bf181a",
  "reviewStatus": "PENDING",
  "analystId": null,
  "analystNotes": "Flagged automatically due to risk score between 0.3 and 0.75",
  "resolvedAt": null
}
```

---

### 2.2 `GET /api/v1/transactions`
Retrieves a paginated or filtered list of transactions.

**Query Parameters**:
- `status` (optional): `APPROVE`, `FLAGGED`, `BLOCK`, `PENDING`

**Response (`200 OK`)**:
```json
[
  {
    "id": "c76a911e-9273-4556-9a2c-b4bb13d78912",
    "transactionRef": "TX-948201",
    "userId": "USR-8472",
    "amount": 389.50,
    "currency": "USD",
    "status": "FLAGGED",
    "fraudProbability": 0.5420,
    "riskLevel": "MEDIUM",
    "createdAt": "2026-09-17T06:40:15.123Z"
  }
]
```

---

### 2.3 `PATCH /api/v1/reviews/transactions/{transactionId}`
Submits a human analyst resolution for a flagged transaction.

**Path Parameter**:
- `transactionId`: UUID of the transaction

**Request Body (`ReviewDecisionRequest`)**:
```json
{
  "analystId": "analyst_sarah_connor",
  "reviewStatus": "CONFIRMED_FRAUD",
  "analystNotes": "Customer confirmed unapproved card activity on recipient domain"
}
```

**Response (`200 OK` - `TransactionResponse`)**:
```json
{
  "id": "c76a911e-9273-4556-9a2c-b4bb13d78912",
  "transactionRef": "TX-948201",
  "status": "BLOCK",
  "reviewStatus": "CONFIRMED_FRAUD",
  "analystId": "analyst_sarah_connor",
  "analystNotes": "Customer confirmed unapproved card activity on recipient domain",
  "resolvedAt": "2026-09-17T06:45:00.000Z"
}
```

---

### 2.4 `GET /api/v1/reviews/flagged`
Returns all open review cases needing analyst action.

---

### 2.5 `GET /api/v1/metrics`
Proxies model performance metrics from `ml-service` to the React dashboard.
