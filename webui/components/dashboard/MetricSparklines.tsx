'use client';

import React, { useEffect, useState } from 'react';
import { getMetrics } from '@/lib/api/system';
import type { Metrics } from '@/lib/types';
import styles from './MetricSparklines.module.css';

export default function MetricSparklines() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = async () => {
    try {
      setError(null);
      const data = await getMetrics();
      setMetrics(data);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch metrics');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, []);

  const formatNumber = (num: number): string => {
    return num.toLocaleString();
  };

  const formatPercentage = (num: number): string => {
    return `${(num * 100).toFixed(1)}%`;
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <h2 className={styles.title}>Metrics</h2>
        <div className={styles.loading}>Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <h2 className={styles.title}>Metrics</h2>
        <div className={styles.error}>Error: {error}</div>
      </div>
    );
  }

  if (!metrics) return null;

  return (
    <div className={styles.container}>
      <h2 className={styles.title}>Metrics</h2>
      <div className={styles.grid}>
        <div className={styles.metric}>
          <div className={styles.metricLabel}>Digests Today</div>
          <div className={styles.metricValue}>{formatNumber(metrics.digests_today)}</div>
          <div className={styles.metricIcon}>📊</div>
        </div>

        <div className={styles.metric}>
          <div className={styles.metricLabel}>API Calls Total</div>
          <div className={styles.metricValue}>{formatNumber(metrics.api_calls_total)}</div>
          <div className={styles.metricIcon}>🔄</div>
        </div>

        <div className={styles.metric}>
          <div className={styles.metricLabel}>Delivery Success Rate</div>
          <div className={styles.metricValue}>
            {formatPercentage(metrics.delivery_success_rate)}
          </div>
          <div className={styles.metricIcon}>✉️</div>
        </div>
      </div>
    </div>
  );
}
