# Fraud Detection Dashboard (`dashboard`)

A modern React (Vite + TypeScript) analyst portal for monitoring transactions, reviewing flagged/blocked cases, inspecting model confidence scores, and visualizing ML evaluation metrics.

---

## Features
- **Real-time Transaction Feed**: Displays transaction IDs, amounts, cards, device fingerprints, and model fraud scores.
- **Decision Filters**: Instantly switch between `All`, `Flagged`, `Blocked`, and `Approved` transactions.
- **Case Review Modal**: Deep-dive into individual transactions, view top risk factors from the ML model, and submit human verdicts (`CONFIRMED_FRAUD` or `FALSE_POSITIVE`).
- **Model Performance Overview**: Live display of critical imbalanced-learning metrics:
  - AUC-PR (Area Under Precision-Recall Curve)
  - Precision & Recall
  - F1-Score & ROC-AUC
  - Test Set Confusion Matrix (TN, FP, FN, TP)

---

## Directory Structure
```
dashboard/
├── src/
│   ├── components/
│   │   ├── Header.tsx
│   │   ├── MetricsOverview.tsx
│   │   ├── TransactionDetailsModal.tsx
│   │   └── TransactionTable.tsx
│   ├── services/
│   │   └── api.ts
│   ├── types/
│   │   └── transaction.ts
│   ├── App.tsx
│   ├── index.css
│   └── main.tsx
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── Dockerfile
```

---

## Local Setup & Run

### 1. Install Dependencies
```bash
cd dashboard
npm install
```

### 2. Start Development Server
```bash
npm run dev
```
The dashboard will open at [http://localhost:5173](http://localhost:5173).

### 3. Production Build
```bash
npm run build
npm run preview
```
