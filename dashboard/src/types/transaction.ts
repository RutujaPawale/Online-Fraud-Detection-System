export type DecisionStatus = 'APPROVE' | 'FLAGGED' | 'BLOCK' | 'PENDING';
export type ReviewStatus = 'PENDING' | 'CONFIRMED_FRAUD' | 'FALSE_POSITIVE';

export interface RiskFactor {
  feature: string;
  contribution: number;
  description: string;
}

export interface Transaction {
  id: string;
  transactionRef: string;
  userId: string;
  amount: number;
  currency: string;
  productCd: string;
  card4?: string;
  card6?: string;
  pEmailDomain?: string;
  rEmailDomain?: string;
  deviceType?: string;
  deviceInfo?: string;
  status: DecisionStatus;
  createdAt: string;

  // ML Fraud Assessment
  fraudProbability?: number;
  riskLevel?: string;
  modelVersion?: string;
  riskFactorsJson?: string;

  // Human Review Case
  reviewCaseId?: string;
  reviewStatus?: ReviewStatus;
  analystId?: string;
  analystNotes?: string;
  resolvedAt?: string;
}

export interface ConfusionMatrix {
  true_negatives: number;
  false_positives: number;
  false_negatives: number;
  true_positives: number;
}

export interface ModelMetrics {
  model_name: string;
  model_version: string;
  imbalance_handling: string;
  evaluation_dataset: string;
  precision: number;
  recall: number;
  f1_score: number;
  auc_pr: number;
  roc_auc: number;
  optimal_threshold: number;
  confusion_matrix: ConfusionMatrix;
  evaluated_at: string;
}

export interface ReviewDecisionRequest {
  analystId: string;
  reviewStatus: 'CONFIRMED_FRAUD' | 'FALSE_POSITIVE';
  analystNotes?: string;
}
