import React from 'react';
import { ModelMetrics } from '../types/transaction';
import { Activity, Target, AlertTriangle, CheckCircle, BarChart3 } from 'lucide-react';

interface MetricsOverviewProps {
  metrics: ModelMetrics | null;
}

export const MetricsOverview: React.FC<MetricsOverviewProps> = ({ metrics }) => {
  if (!metrics) return null;

  const cm = metrics.confusion_matrix;

  return (
    <div style={{ marginBottom: '2rem' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '1rem'
      }}>
        <div>
          <h2 style={{ fontSize: '1.1rem', fontWeight: '600' }}>Model Performance & Evaluation</h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Evaluated on {metrics.evaluation_dataset} with {metrics.imbalance_handling}
          </p>
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          Decision Threshold: <strong style={{ color: '#F3F4F6' }}>{metrics.optimal_threshold}</strong>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '1rem',
        marginBottom: '1.25rem'
      }}>
        <div style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '1.25rem'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>AUC-PR</span>
            <Target size={18} color="#818CF8" />
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: '700', color: '#818CF8' }}>
            {(metrics.auc_pr * 100).toFixed(1)}%
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            Primary metric for class-imbalance
          </div>
        </div>

        <div style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '1.25rem'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Precision</span>
            <CheckCircle size={18} color="#34D399" />
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: '700', color: '#34D399' }}>
            {(metrics.precision * 100).toFixed(1)}%
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            Low false-positive rate
          </div>
        </div>

        <div style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '1.25rem'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Recall (Sensitivity)</span>
            <AlertTriangle size={18} color="#FBBF24" />
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: '700', color: '#FBBF24' }}>
            {(metrics.recall * 100).toFixed(1)}%
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            Frauds successfully captured
          </div>
        </div>

        <div style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '1.25rem'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>F1-Score</span>
            <Activity size={18} color="#60A5FA" />
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: '700', color: '#60A5FA' }}>
            {(metrics.f1_score * 100).toFixed(1)}%
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            Harmonic balance of PR
          </div>
        </div>

        <div style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '1.25rem'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>ROC-AUC</span>
            <BarChart3 size={18} color="#A78BFA" />
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: '700', color: '#A78BFA' }}>
            {(metrics.roc_auc * 100).toFixed(1)}%
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            Global discrimination ability
          </div>
        </div>
      </div>

      {/* Confusion Matrix Display */}
      <div style={{
        backgroundColor: 'var(--bg-card)',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        padding: '1.25rem'
      }}>
        <div style={{ fontSize: '0.85rem', fontWeight: '600', marginBottom: '0.85rem' }}>
          Test Set Confusion Matrix
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: '0.75rem',
          maxWidth: '600px'
        }}>
          <div style={{
            backgroundColor: 'rgba(16, 185, 129, 0.08)',
            border: '1px solid rgba(16, 185, 129, 0.2)',
            borderRadius: '6px',
            padding: '0.75rem'
          }}>
            <div style={{ fontSize: '0.75rem', color: '#34D399' }}>True Negatives (TN)</div>
            <div style={{ fontSize: '1.2rem', fontWeight: '700', color: '#F9FAFB' }}>
              {cm.true_negatives.toLocaleString()}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Legitimate transactions approved</div>
          </div>

          <div style={{
            backgroundColor: 'rgba(245, 158, 11, 0.08)',
            border: '1px solid rgba(245, 158, 11, 0.2)',
            borderRadius: '6px',
            padding: '0.75rem'
          }}>
            <div style={{ fontSize: '0.75rem', color: '#FBBF24' }}>False Positives (FP)</div>
            <div style={{ fontSize: '1.2rem', fontWeight: '700', color: '#F9FAFB' }}>
              {cm.false_positives.toLocaleString()}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Legitimate flagged / blocked</div>
          </div>

          <div style={{
            backgroundColor: 'rgba(239, 68, 68, 0.08)',
            border: '1px solid rgba(239, 68, 68, 0.2)',
            borderRadius: '6px',
            padding: '0.75rem'
          }}>
            <div style={{ fontSize: '0.75rem', color: '#F87171' }}>False Negatives (FN)</div>
            <div style={{ fontSize: '1.2rem', fontWeight: '700', color: '#F9FAFB' }}>
              {cm.false_negatives.toLocaleString()}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Missed fraud cases</div>
          </div>

          <div style={{
            backgroundColor: 'rgba(99, 102, 241, 0.08)',
            border: '1px solid rgba(99, 102, 241, 0.2)',
            borderRadius: '6px',
            padding: '0.75rem'
          }}>
            <div style={{ fontSize: '0.75rem', color: '#818CF8' }}>True Positives (TP)</div>
            <div style={{ fontSize: '1.2rem', fontWeight: '700', color: '#F9FAFB' }}>
              {cm.true_positives.toLocaleString()}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Fraudulent transactions caught</div>
          </div>
        </div>
      </div>
    </div>
  );
};
