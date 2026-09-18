import React, { useState } from 'react';
import { Transaction, RiskFactor } from '../types/transaction';
import { X, ShieldAlert, CheckCircle, XCircle, AlertTriangle, UserCheck } from 'lucide-react';

interface TransactionDetailsModalProps {
  transaction: Transaction | null;
  onClose: () => void;
  onSubmitReview: (transactionId: string, status: 'CONFIRMED_FRAUD' | 'FALSE_POSITIVE', notes: string) => Promise<void>;
}

export const TransactionDetailsModal: React.FC<TransactionDetailsModalProps> = ({
  transaction,
  onClose,
  onSubmitReview,
}) => {
  const [analystNotes, setAnalystNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!transaction) return null;

  let riskFactors: RiskFactor[] = [];
  if (transaction.riskFactorsJson) {
    try {
      riskFactors = JSON.parse(transaction.riskFactorsJson);
    } catch {
      riskFactors = [];
    }
  }

  const handleReviewAction = async (status: 'CONFIRMED_FRAUD' | 'FALSE_POSITIVE') => {
    setIsSubmitting(true);
    try {
      await onSubmitReview(transaction.id, status, analystNotes);
      onClose();
    } catch (err) {
      console.error("Failed to submit review:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div style={{
          padding: '1.25rem 1.5rem',
          borderBottom: '1px solid var(--border-color)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <ShieldAlert size={20} color="#818CF8" />
            <h3 style={{ fontSize: '1.1rem', fontWeight: '600' }}>
              Transaction Review: {transaction.transactionRef}
            </h3>
          </div>
          <button
            onClick={onClose}
            style={{ backgroundColor: 'transparent', color: 'var(--text-muted)' }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: '1.5rem' }}>
          {/* Key Metrics Strip */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '0.75rem',
            marginBottom: '1.5rem'
          }}>
            <div style={{ backgroundColor: '#0B0F19', padding: '0.85rem', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Amount</div>
              <div style={{ fontSize: '1.2rem', fontWeight: '700' }}>
                ${transaction.amount.toFixed(2)} {transaction.currency}
              </div>
            </div>

            <div style={{ backgroundColor: '#0B0F19', padding: '0.85rem', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Fraud Probability</div>
              <div style={{
                fontSize: '1.2rem',
                fontWeight: '700',
                color: (transaction.fraudProbability || 0) >= 0.75 ? '#F87171' : (transaction.fraudProbability || 0) >= 0.3 ? '#FBBF24' : '#34D399'
              }}>
                {transaction.fraudProbability !== undefined ? `${(transaction.fraudProbability * 100).toFixed(1)}%` : 'N/A'}
              </div>
            </div>

            <div style={{ backgroundColor: '#0B0F19', padding: '0.85rem', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Current Status</div>
              <div style={{ fontSize: '1.1rem', fontWeight: '700', color: '#E2E8F0' }}>
                {transaction.status}
              </div>
            </div>
          </div>

          {/* Feature Breakdown */}
          <div style={{ marginBottom: '1.5rem' }}>
            <h4 style={{ fontSize: '0.9rem', fontWeight: '600', marginBottom: '0.6rem', color: '#94A3B8' }}>
              IEEE-CIS Transaction & Identity Features
            </h4>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: '0.5rem',
              fontSize: '0.8rem',
              backgroundColor: '#0B0F19',
              padding: '0.85rem',
              borderRadius: '6px'
            }}>
              <div><span style={{ color: 'var(--text-muted)' }}>Product Code:</span> {transaction.productCd}</div>
              <div><span style={{ color: 'var(--text-muted)' }}>Card Network:</span> {transaction.card4 || 'N/A'} ({transaction.card6 || 'N/A'})</div>
              <div><span style={{ color: 'var(--text-muted)' }}>Purchaser Email:</span> {transaction.pEmailDomain || 'N/A'}</div>
              <div><span style={{ color: 'var(--text-muted)' }}>Recipient Email:</span> {transaction.rEmailDomain || 'N/A'}</div>
              <div><span style={{ color: 'var(--text-muted)' }}>Device Type:</span> {transaction.deviceType || 'N/A'}</div>
              <div><span style={{ color: 'var(--text-muted)' }}>Device Info:</span> {transaction.deviceInfo || 'N/A'}</div>
            </div>
          </div>

          {/* Model Risk Factors */}
          <div style={{ marginBottom: '1.5rem' }}>
            <h4 style={{ fontSize: '0.9rem', fontWeight: '600', marginBottom: '0.6rem', color: '#94A3B8' }}>
              Influential Model Risk Factors
            </h4>
            {riskFactors.length === 0 ? (
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>No elevated risk factors detected for this transaction.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {riskFactors.map((rf, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.6rem',
                      padding: '0.65rem 0.85rem',
                      backgroundColor: 'rgba(239, 68, 68, 0.08)',
                      border: '1px solid rgba(239, 68, 68, 0.2)',
                      borderRadius: '6px',
                      fontSize: '0.8rem'
                    }}
                  >
                    <AlertTriangle size={16} color="#F87171" style={{ flexShrink: 0 }} />
                    <div style={{ flex: 1 }}>
                      <span style={{ fontWeight: '600', color: '#FCA5A5' }}>{rf.feature}</span>: {rf.description}
                    </div>
                    <span style={{ color: '#F87171', fontWeight: '700' }}>
                      +{Math.round(rf.contribution * 100)}%
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Analyst Review Section */}
          <div style={{
            borderTop: '1px solid var(--border-color)',
            paddingTop: '1.25rem'
          }}>
            <h4 style={{ fontSize: '0.9rem', fontWeight: '600', marginBottom: '0.6rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <UserCheck size={16} color="#818CF8" />
              <span>Analyst Decision Action</span>
            </h4>

            {transaction.reviewStatus && transaction.reviewStatus !== 'PENDING' ? (
              <div style={{
                padding: '0.75rem',
                backgroundColor: '#0B0F19',
                borderRadius: '6px',
                fontSize: '0.85rem'
              }}>
                <div>Resolved as: <strong>{transaction.reviewStatus}</strong></div>
                {transaction.analystNotes && (
                  <div style={{ color: 'var(--text-muted)', marginTop: '0.25rem', fontSize: '0.8rem' }}>
                    Notes: {transaction.analystNotes}
                  </div>
                )}
              </div>
            ) : (
              <div>
                <textarea
                  placeholder="Enter analyst review justification notes..."
                  value={analystNotes}
                  onChange={(e) => setAnalystNotes(e.target.value)}
                  style={{
                    width: '100%',
                    height: '70px',
                    backgroundColor: '#0B0F19',
                    border: '1px solid var(--border-color)',
                    borderRadius: '6px',
                    padding: '0.5rem 0.75rem',
                    color: '#F9FAFB',
                    fontSize: '0.8rem',
                    marginBottom: '0.85rem',
                    resize: 'none'
                  }}
                />

                <div style={{ display: 'flex', gap: '0.75rem' }}>
                  <button
                    onClick={() => handleReviewAction('CONFIRMED_FRAUD')}
                    disabled={isSubmitting}
                    style={{
                      flex: 1,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '0.4rem',
                      padding: '0.6rem',
                      backgroundColor: 'rgba(239, 68, 68, 0.2)',
                      border: '1px solid rgba(239, 68, 68, 0.4)',
                      color: '#FCA5A5',
                      borderRadius: '6px',
                      fontWeight: '600',
                      fontSize: '0.85rem'
                    }}
                  >
                    <XCircle size={16} />
                    <span>Confirm Fraud (Block)</span>
                  </button>

                  <button
                    onClick={() => handleReviewAction('FALSE_POSITIVE')}
                    disabled={isSubmitting}
                    style={{
                      flex: 1,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '0.4rem',
                      padding: '0.6rem',
                      backgroundColor: 'rgba(16, 185, 129, 0.2)',
                      border: '1px solid rgba(16, 185, 129, 0.4)',
                      color: '#6EE7B7',
                      borderRadius: '6px',
                      fontWeight: '600',
                      fontSize: '0.85rem'
                    }}
                  >
                    <CheckCircle size={16} />
                    <span>False Positive (Approve)</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
