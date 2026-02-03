'use client';

import React, { useEffect, useState } from 'react';
import { getHealth } from '@/lib/api/system';
import type { HealthStatus, ComponentHealth } from '@/lib/types';
import styles from './SystemPulse.module.css';

export default function SystemPulse() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = async () => {
    try {
      setError(null);
      const data = await getHealth();
      setHealth(data);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch health status');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 15000); // Poll every 15s
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'healthy': return 'var(--md-color-success)';
      case 'degraded': return 'var(--md-color-warning)';
      case 'unhealthy': return 'var(--md-color-danger)';
      default: return 'var(--md-color-text-tertiary)';
    }
  };

  const getStatusIcon = (status: string): string => {
    switch (status) {
      case 'healthy': return '✓';
      case 'degraded': return '⚠';
      case 'unhealthy': return '✗';
      default: return '?';
    }
  };

  const renderComponent = (name: string, component: ComponentHealth) => (
    <div key={name} className={styles.component}>
      <div className={styles.componentHeader}>
        <span className={styles.componentName}>{name}</span>
        <span
          className={styles.statusBadge}
          style={{ backgroundColor: getStatusColor(component.status) }}
        >
          {getStatusIcon(component.status)} {component.status}
        </span>
      </div>
      <p className={styles.componentMessage}>{component.message}</p>
      {component.latency_ms !== undefined && (
        <p className={styles.latency}>{component.latency_ms}ms</p>
      )}
    </div>
  );

  if (loading) {
    return (
      <div className={styles.container}>
        <h2 className={styles.title}>System Pulse</h2>
        <div className={styles.loading}>Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <h2 className={styles.title}>System Pulse</h2>
        <div className={styles.error}>Error: {error}</div>
      </div>
    );
  }

  if (!health) return null;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>System Pulse</h2>
        <div
          className={styles.overallStatus}
          style={{ backgroundColor: getStatusColor(health.status) }}
        >
          {getStatusIcon(health.status)} {health.status}
        </div>
      </div>
      <div className={styles.components}>
        {renderComponent('Database', health.components.database)}
        {renderComponent('Redis', health.components.redis)}
        {renderComponent('Celery', health.components.celery)}
      </div>
    </div>
  );
}
