import { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { MetricsOverview } from './components/MetricsOverview';
import { TransactionTable } from './components/TransactionTable';
import { TransactionDetailsModal } from './components/TransactionDetailsModal';
import { Transaction, DecisionStatus, ModelMetrics } from './types/transaction';
import { fetchTransactions, fetchModelMetrics, submitReview } from './services/api';

export function App() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [metrics, setMetrics] = useState<ModelMetrics | null>(null);
  const [filter, setFilter] = useState<DecisionStatus | 'ALL'>('ALL');
  const [selectedTx, setSelectedTx] = useState<Transaction | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [txList, modelMetrics] = await Promise.all([
        fetchTransactions(filter === 'ALL' ? undefined : filter),
        fetchModelMetrics()
      ]);
      setTransactions(txList);
      setMetrics(modelMetrics);
    } catch (err) {
      console.error("Error fetching dashboard data:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [filter]);

  const handleReviewSubmit = async (
    transactionId: string,
    status: 'CONFIRMED_FRAUD' | 'FALSE_POSITIVE',
    notes: string
  ) => {
    const updated = await submitReview(transactionId, {
      analystId: "analyst_sarah_connor",
      reviewStatus: status,
      analystNotes: notes
    });

    setTransactions((prev) =>
      prev.map((t) => (t.id === transactionId ? updated : t))
    );
    setSelectedTx(null);
  };

  return (
    <div>
      <Header onRefresh={loadData} isLoading={isLoading} />
      
      <main className="container">
        <MetricsOverview metrics={metrics} />
        
        <div style={{ marginTop: '2rem' }}>
          <div style={{ marginBottom: '0.75rem' }}>
            <h2 style={{ fontSize: '1.1rem', fontWeight: '600' }}>Live Ingested Transactions</h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Real-time feed processed by the Spring Boot decision engine & Python ML service
            </p>
          </div>

          <TransactionTable
            transactions={transactions}
            selectedStatusFilter={filter}
            onFilterChange={setFilter}
            onSelectTransaction={setSelectedTx}
          />
        </div>
      </main>

      <TransactionDetailsModal
        transaction={selectedTx}
        onClose={() => setSelectedTx(null)}
        onSubmitReview={handleReviewSubmit}
      />
    </div>
  );
}

export default App;
