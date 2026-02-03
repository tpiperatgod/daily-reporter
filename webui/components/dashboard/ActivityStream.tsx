'use client';

import React, { useEffect, useState } from 'react';
import { getActivity } from '@/lib/api/system';
import type { ActivityResponse, ActivityLog } from '@/lib/types';
import styles from './ActivityStream.module.css';

export default function ActivityStream() {
  const [activity, setActivity] = useState<ActivityLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchActivity = async () => {
    try {
      setError(null);
      const data: ActivityResponse = await getActivity();
      setActivity(data.items);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch activity');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActivity();
    const interval = setInterval(fetchActivity, 10000); // Poll every 10s
    return () => clearInterval(interval);
  }, []);

  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);

    if (minutes < 1) return 'just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return date.toLocaleDateString();
  };

  const getTypeColor = (type: string): string => {
    switch (type) {
      case 'success': return 'var(--md-color-success)';
      case 'warning': return 'var(--md-color-warning)';
      case 'error': return 'var(--md-color-danger)';
      case 'info':
      default: return 'var(--md-color-primary)';
    }
  };

  const getTypeIcon = (type: string): string => {
    switch (type) {
      case 'success': return '✓';
      case 'warning': return '⚠';
      case 'error': return '✗';
      case 'info':
      default: return 'ℹ';
    }
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <h2 className={styles.title}>Activity Stream</h2>
        <div className={styles.loading}>Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <h2 className={styles.title}>Activity Stream</h2>
        <div className={styles.error}>Error: {error}</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <h2 className={styles.title}>Activity Stream</h2>
      <div className={styles.stream}>
        {activity.length === 0 ? (
          <div className={styles.empty}>No recent activity</div>
        ) : (
          activity.map((log) => (
            <div key={log.id} className={styles.logItem}>
              <div
                className={styles.typeIndicator}
                style={{ backgroundColor: getTypeColor(log.type) }}
              >
                {getTypeIcon(log.type)}
              </div>
              <div className={styles.logContent}>
                <div className={styles.logMessage}>{log.message}</div>
                <div className={styles.logTimestamp}>
                  {formatTimestamp(log.timestamp)}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
