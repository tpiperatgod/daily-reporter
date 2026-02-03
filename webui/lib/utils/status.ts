export type StatusType = 'healthy' | 'degraded' | 'unhealthy' | 'pending' | 'success' | 'failed';

export function getStatusColor(status: StatusType): string {
  const colors = {
    healthy: 'var(--color-success)',
    success: 'var(--color-success)',
    degraded: 'var(--color-warning)',
    pending: 'var(--color-warning)',
    unhealthy: 'var(--color-error)',
    failed: 'var(--color-error)',
  };

  return colors[status] || 'var(--color-text-secondary)';
}

export function getStatusLabel(status: StatusType): string {
  const labels = {
    healthy: 'Healthy',
    success: 'Success',
    degraded: 'Degraded',
    pending: 'Pending',
    unhealthy: 'Unhealthy',
    failed: 'Failed',
  };

  return labels[status] || status;
}
