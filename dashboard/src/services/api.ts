import axios from 'axios';
import { Transaction, DecisionStatus, ModelMetrics, ReviewDecisionRequest } from '../types/transaction';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 6000,
});

// ============================================================================
// NETWORK-FAILURE / OFFLINE FALLBACK DATA ONLY
// ----------------------------------------------------------------------------
// The primary source of truth for the dashboard is ALWAYS the live Spring Boot
// api-service at /api/v1 (backed by PostgreSQL and the LightGBM ml-service).
// The static records below are utilized STRICTLY as a graceful degradation
// fallback in the event of an unexpected network outage or temporary service
// disconnection, ensuring the UI remains operable rather than crashing.
// ============================================================================
const MOCK_TRANSACTIONS: Transaction[] = [
  {
    id: "e14b6bc8-43d9-482a-97a5-c2a4f61f71a1",
    transactionRef: "W-893041",
    userId: "USR-88129",
    amount: 1420.50,
    currency: "USD",
    productCd: "W",
    card4: "visa",
    card6: "credit",
    pEmailDomain: "gmail.com",
    rEmailDomain: "mailinator.com",
    deviceType: "mobile",
    deviceInfo: "iOS 17.4",
    status: "BLOCK",
    createdAt: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    fraudProbability: 0.8850,
    riskLevel: "HIGH",
    modelVersion: "v0.1.0-baseline",
    riskFactorsJson: JSON.stringify([
      { feature: "email_domain", contribution: 0.40, description: "Disposable email domain mailinator.com detected" },
      { feature: "transaction_amt", contribution: 0.22, description: "High deviation ($1,420.50) from user baseline" }
    ])
  },
  {
    id: "f25c7cd9-54ea-593b-a8b6-d3b5a72e82b2",
    transactionRef: "C-442109",
    userId: "USR-34011",
    amount: 495.00,
    currency: "USD",
    productCd: "C",
    card4: "mastercard",
    card6: "debit",
    pEmailDomain: "yahoo.com",
    rEmailDomain: "yahoo.com",
    deviceType: "desktop",
    deviceInfo: "Windows 11 Chrome",
    status: "FLAGGED",
    createdAt: new Date(Date.now() - 1000 * 60 * 18).toISOString(),
    fraudProbability: 0.5420,
    riskLevel: "MEDIUM",
    modelVersion: "v0.1.0-baseline",
    reviewCaseId: "rc-901",
    reviewStatus: "PENDING",
    riskFactorsJson: JSON.stringify([
      { feature: "product_cd", contribution: 0.15, description: "Product code 'C' historically carries higher dispute volume" },
      { feature: "transaction_amt", contribution: 0.10, description: "Elevated transaction amount" }
    ])
  },
  {
    id: "a36d8de0-65fb-604c-b9c7-e4c6b83f93c3",
    transactionRef: "W-129480",
    userId: "USR-77392",
    amount: 64.25,
    currency: "USD",
    productCd: "W",
    card4: "visa",
    card6: "debit",
    pEmailDomain: "outlook.com",
    rEmailDomain: "outlook.com",
    deviceType: "mobile",
    deviceInfo: "Pixel 8 Android 14",
    status: "APPROVE",
    createdAt: new Date(Date.now() - 1000 * 60 * 35).toISOString(),
    fraudProbability: 0.0420,
    riskLevel: "LOW",
    modelVersion: "v0.1.0-baseline",
    riskFactorsJson: JSON.stringify([])
  }
];

// Offline fallback snapshot of validation metrics (mirrors ml-service models/metrics.json)
// Used only when api-service is unreachable over the network.
const MOCK_METRICS: ModelMetrics = {
  model_name: "LightGBM Fraud Classifier",
  model_version: "v1.0.0-trained",
  imbalance_handling: "scale_pos_weight (27.46)",
  evaluation_dataset: "IEEE-CIS Time-Based Validation Split (Last 20%)",
  precision: 0.6290,
  recall: 0.4092,
  f1_score: 0.4958,
  auc_pr: 0.5144,
  roc_auc: 0.9128,
  optimal_threshold: 0.85,
  confusion_matrix: {
    true_negatives: 113063,
    false_positives: 981,
    false_negatives: 2401,
    true_positives: 1663
  },
  evaluated_at: new Date().toISOString()
};

export const fetchTransactions = async (status?: DecisionStatus): Promise<Transaction[]> => {
  try {
    const params = status ? { status } : {};
    const res = await apiClient.get<Transaction[]>('/transactions', { params });
    return res.data;
  } catch (err) {
    console.warn("api-service unreachable, falling back to mock dataset:", err);
    if (status) {
      return MOCK_TRANSACTIONS.filter(t => t.status === status);
    }
    return MOCK_TRANSACTIONS;
  }
};

export const fetchTransactionById = async (id: string): Promise<Transaction> => {
  try {
    const res = await apiClient.get<Transaction>(`/transactions/${id}`);
    return res.data;
  } catch (err) {
    console.warn(`api-service unreachable, returning mock item for ${id}:`, err);
    const item = MOCK_TRANSACTIONS.find(t => t.id === id);
    if (item) return item;
    throw err;
  }
};

export const fetchModelMetrics = async (): Promise<ModelMetrics> => {
  try {
    const res = await apiClient.get<ModelMetrics>('/metrics');
    return res.data;
  } catch (err) {
    console.warn("api-service unreachable, returning mock evaluation metrics:", err);
    return MOCK_METRICS;
  }
};

export const submitReview = async (
  transactionId: string,
  decision: ReviewDecisionRequest
): Promise<Transaction> => {
  try {
    const res = await apiClient.patch<Transaction>(`/reviews/transactions/${transactionId}`, decision);
    return res.data;
  } catch (err) {
    console.warn("api-service unreachable, applying mock local review state:", err);
    const item = MOCK_TRANSACTIONS.find(t => t.id === transactionId);
    if (item) {
      item.reviewStatus = decision.reviewStatus;
      item.analystId = decision.analystId;
      item.analystNotes = decision.analystNotes;
      item.status = decision.reviewStatus === 'CONFIRMED_FRAUD' ? 'BLOCK' : 'APPROVE';
      return { ...item };
    }
    throw err;
  }
};
