import React, { useState } from 'react';
import { Transaction, DecisionStatus } from '../types/transaction';
import { Search, ChevronRight, AlertCircle, CheckCircle2, XCircle, Clock } from 'lucide-react';

interface TransactionTableProps {
  transactions: Transaction[];
  onSelectTransaction: (tx: Transaction) => void;
  selectedStatusFilter: DecisionStatus | 'ALL';
  onFilterChange: (status: DecisionStatus | 'ALL') => void;
}

export const TransactionTable: React.FC<TransactionTableProps> = ({
  transactions,
  onSelectTransaction,
  selectedStatusFilter,
  onFilterChange,
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  const filtered = transactions.filter((tx) => {
    const matchesSearch =
      tx.transactionRef.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (tx.pEmailDomain && tx.pEmailDomain.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (tx.userId && tx.userId.toLowerCase().includes(searchQuery.toLowerCase()));

    if (!matchesSearch) return false;
    if (selectedStatusFilter === 'ALL') return true;
    return tx.status === selectedStatusFilter;
  });

  // Default sort: descending by creation timestamp (most recent transactions at the top)
  const sortedAndFiltered = [...filtered].sort((a, b) => {
    const timeA = a.createdAt ? new Date(a.createdAt).getTime() : 0;
    const timeB = b.createdAt ? new Date(b.createdAt).getTime() : 0;
    return timeB - timeA;
  });

  const getStatusBadge = (status: DecisionStatus) => {
    switch (status) {
      case 'APPROVE':
        return (
          <span className="badge badge-APPROVE">
            <CheckCircle2 size={12} /> Approved
          </span>
        );
      case 'FLAGGED':
        return (
          <span className="badge badge-FLAGGED">
            <AlertCircle size={12} /> Flagged
          </span>
        );
      case 'BLOCK':
        return (
          <span className="badge badge-BLOCK">
            <XCircle size={12} /> Blocked
          </span>
        );
      default:
        return (
          <span className="badge badge-PENDING">
            <Clock size={12} /> Pending
          </span>
        );
    }
  };

  const getScoreColor = (prob?: number) => {
    if (prob === undefined) return '#9CA3AF';
    if (prob >= 0.75) return '#F87171'; // High
    if (prob >= 0.30) return '#FBBF24'; // Medium
    return '#34D399'; // Low
  };

  return (
    <div style={{
      backgroundColor: 'var(--bg-card)',
      border: '1px solid var(--border-color)',
      borderRadius: '8px',
      overflow: 'hidden'
    }}>
      {/* Controls Bar */}
      <div style={{
        padding: '1rem 1.25rem',
        borderBottom: '1px solid var(--border-color)',
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '1rem'
      }}>
        {/* Filter Tabs */}
        <div style={{ display: 'flex', gap: '0.5rem', backgroundColor: '#0B0F19', padding: '0.25rem', borderRadius: '6px' }}>
          {(['ALL', 'FLAGGED', 'BLOCK', 'APPROVE'] as const).map((status) => (
            <button
              key={status}
              onClick={() => onFilterChange(status)}
              style={{
                padding: '0.35rem 0.85rem',
                borderRadius: '4px',
                fontSize: '0.8rem',
                fontWeight: '600',
                backgroundColor: selectedStatusFilter === status ? '#374151' : 'transparent',
                color: selectedStatusFilter === status ? '#FFFFFF' : 'var(--text-muted)'
              }}
            >
              {status === 'ALL' ? 'All Transactions' : status.charAt(0) + status.slice(1).toLowerCase()}
            </button>
          ))}
        </div>

        {/* Search */}
        <div style={{ position: 'relative', width: '280px' }}>
          <Search size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)' }} />
          <input
            type="text"
            placeholder="Search ref, user, or domain..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '0.45rem 0.75rem 0.45rem 2.2rem',
              backgroundColor: '#0B0F19',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              color: '#F9FAFB',
              fontSize: '0.85rem',
              outline: 'none'
            }}
          />
        </div>
      </div>

      {/* Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
          <thead>
            <tr style={{
              borderBottom: '1px solid var(--border-color)',
              color: 'var(--text-muted)',
              fontSize: '0.75rem',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              backgroundColor: 'rgba(0, 0, 0, 0.2)'
            }}>
              <th style={{ padding: '0.75rem 1.25rem' }}>Transaction Ref</th>
              <th style={{ padding: '0.75rem 1rem' }}>User & Email</th>
              <th style={{ padding: '0.75rem 1rem' }}>Amount</th>
              <th style={{ padding: '0.75rem 1rem' }}>Product / Card</th>
              <th style={{ padding: '0.75rem 1rem' }}>Device</th>
              <th style={{ padding: '0.75rem 1rem' }}>Fraud Score</th>
              <th style={{ padding: '0.75rem 1rem' }}>Decision</th>
              <th style={{ padding: '0.75rem 1.25rem', textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {sortedAndFiltered.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ padding: '2.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No transactions found matching criteria.
                </td>
              </tr>
            ) : (
              sortedAndFiltered.map((tx) => (
                <tr
                  key={tx.id}
                  style={{
                    borderBottom: '1px solid #1F2937',
                    transition: 'background-color 0.15s ease'
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-card-hover)')}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <td style={{ padding: '0.85rem 1.25rem', fontWeight: '600', color: '#E2E8F0' }}>
                    <div>{tx.transactionRef}</div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: '400', marginTop: '0.2rem' }}>
                      {tx.createdAt
                        ? new Date(tx.createdAt).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                            second: '2-digit',
                          }) +
                          ' · ' +
                          new Date(tx.createdAt).toLocaleDateString([], {
                            month: 'short',
                            day: 'numeric',
                          })
                        : 'N/A'}
                    </div>
                  </td>
                  <td style={{ padding: '0.85rem 1rem' }}>
                    <div style={{ color: '#F1F5F9' }}>{tx.userId}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{tx.pEmailDomain || 'N/A'}</div>
                  </td>
                  <td style={{ padding: '0.85rem 1rem', fontWeight: '600' }}>
                    ${tx.amount.toFixed(2)} <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{tx.currency}</span>
                  </td>
                  <td style={{ padding: '0.85rem 1rem' }}>
                    <span style={{
                      backgroundColor: '#374151',
                      padding: '0.15rem 0.45rem',
                      borderRadius: '4px',
                      fontSize: '0.75rem',
                      fontWeight: '600',
                      marginRight: '0.4rem'
                    }}>
                      {tx.productCd}
                    </span>
                    <span style={{ color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                      {tx.card4 || 'card'} {tx.card6 || ''}
                    </span>
                  </td>
                  <td style={{ padding: '0.85rem 1rem', color: 'var(--text-muted)' }}>
                    {tx.deviceType || 'Unknown'} {tx.deviceInfo ? `(${tx.deviceInfo})` : ''}
                  </td>
                  <td style={{ padding: '0.85rem 1rem' }}>
                    {tx.fraudProbability !== undefined ? (
                      <span style={{
                        color: getScoreColor(tx.fraudProbability),
                        fontWeight: '700',
                        fontSize: '0.9rem'
                      }}>
                        {(tx.fraudProbability * 100).toFixed(1)}%
                      </span>
                    ) : (
                      <span style={{ color: 'var(--text-muted)' }}>N/A</span>
                    )}
                  </td>
                  <td style={{ padding: '0.85rem 1rem' }}>
                    {getStatusBadge(tx.status)}
                  </td>
                  <td style={{ padding: '0.85rem 1.25rem', textAlign: 'right' }}>
                    <button
                      onClick={() => onSelectTransaction(tx)}
                      style={{
                        padding: '0.35rem 0.65rem',
                        backgroundColor: '#1E293B',
                        color: '#94A3B8',
                        borderRadius: '6px',
                        fontSize: '0.75rem',
                        fontWeight: '500',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.2rem'
                      }}
                    >
                      <span>Review</span>
                      <ChevronRight size={14} />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
