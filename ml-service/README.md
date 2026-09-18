# Machine Learning Fraud Detection Service (`ml-service`)

A Python FastAPI microservice that provides real-time fraud probability scoring and model evaluation metrics for online transactions, modeled after the IEEE-CIS Fraud Detection dataset.

---

## Features
- **FastAPI REST Endpoint**: `POST /api/v1/score` accepts transaction + identity features and returns fraud probability, categorical risk level (`LOW`, `MEDIUM`, `HIGH`), and contributing risk factors.
- **Model Evaluation Endpoint**: `GET /api/v1/metrics` provides precision, recall, F1, AUC-PR, ROC-AUC, and the confusion matrix.
- **Health & Readiness Check**: `GET /api/v1/health`.
- **IEEE-CIS Dataset Support**: Designed for `train_transaction.csv` + `train_identity.csv` schemas.
- **Imbalance Handling**: Ready for class weighting (`scale_pos_weight`) and SMOTE / cost-sensitive learning to address severe ~3.5% fraud class imbalance.

---

## Directory Structure
```
ml-service/
├── app/
│   ├── api/             # REST route handlers
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── core/            # App settings & configurations
│   │   ├── __init__.py
│   │   └── config.py
│   ├── schemas/         # Pydantic request & response models
│   │   ├── __init__.py
│   │   ├── metrics.py
│   │   ├── prediction.py
│   │   └── transaction.py
│   ├── services/        # Scoring engine & model inference wrapper
│   │   ├── __init__.py
│   │   └── predictor.py
│   ├── __init__.py
│   └── main.py          # FastAPI application factory
├── data/                # Raw & processed CSV dataset storage
├── models/              # Serialized model weights (e.g., fraud_model.joblib)
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Local Setup & Run

### 1. Create Virtual Environment
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Start the Service
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation will be available at:
- Swagger UI: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
- ReDoc: [http://localhost:8000/api/v1/redoc](http://localhost:8000/api/v1/redoc)

---

## API Contract Sample

### Request: `POST /api/v1/score`
```json
{
  "transaction_ref": "TX-109283",
  "transaction_amt": 1250.00,
  "product_cd": "W",
  "card1": "13926",
  "card4": "visa",
  "card6": "credit",
  "p_emaildomain": "gmail.com",
  "r_emaildomain": "mailinator.com",
  "device_type": "mobile",
  "device_info": "iOS 17.4"
}
```

### Response: `200 OK`
```json
{
  "transaction_ref": "TX-109283",
  "fraud_probability": 0.825,
  "risk_level": "HIGH",
  "recommendation": "BLOCK",
  "model_version": "v0.1.0-baseline",
  "risk_factors": [
    {
      "feature": "email_domain",
      "contribution": 0.4,
      "description": "Disposable or anonymized email domain detected"
    },
    {
      "feature": "transaction_amt",
      "contribution": 0.175,
      "description": "High transaction value ($1,250.00) deviates from average"
    }
  ],
  "evaluated_at": "2026-09-17T06:35:00.000Z"
}
```
