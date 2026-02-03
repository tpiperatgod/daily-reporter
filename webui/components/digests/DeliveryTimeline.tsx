'use client';

import { getDigestDeliveries } from '@/lib/api/digests';
import { useApi } from '@/lib/hooks/useApi';
import { formatTimestamp, formatLatency } from '@/lib/utils/format';
import { getStatusColor, getStatusLabel } from '@/lib/utils/status';
import type { Delivery } from '@/lib/types';

interface DeliveryTimelineProps {
  digestId: string;
}

export function DeliveryTimeline({ digestId }: DeliveryTimelineProps) {
  const { data: deliveries } = useApi<Delivery[]>(`/digests/${digestId}/deliveries`, {
    fetcher: () => getDigestDeliveries(digestId),
  });

  if (!deliveries) {
    return <div>Loading deliveries...</div>;
  }

  const failedCount = deliveries.filter((d) => d.status === 'failed').length;

  return (
    <div>
      {failedCount > 0 && (
        <button
          className="w-full mb-4 p-3 rounded-lg font-medium"
          style={{
            backgroundColor: 'var(--color-error)',
            color: 'white',
          }}
        >
          Retry All Failed ({failedCount})
        </button>
      )}

      <div className="space-y-3">
        {deliveries.map((delivery) => (
          <div
            key={delivery.id}
            className="rounded-lg p-4 border"
            style={{
              backgroundColor: 'var(--color-surface-elevated)',
              borderColor: 'var(--color-border)',
            }}
          >
            <div className="flex items-start gap-3">
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center font-bold"
                style={{
                  backgroundColor: 'var(--color-primary)',
                  color: 'white',
                }}
              >
                {delivery.user?.name?.[0] || delivery.user?.email[0].toUpperCase() || '?'}
              </div>
              <div className="flex-1">
                <p className="font-medium">
                  {delivery.user?.name || delivery.user?.email || 'Unknown User'}
                </p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-sm">
                    {delivery.channel === 'feishu' ? 'Feishu' : 'Email'}
                  </span>
                  <span
                    className="px-2 py-1 rounded-full text-xs"
                    style={{
                      backgroundColor: getStatusColor(delivery.status) + '20',
                      color: getStatusColor(delivery.status),
                    }}
                  >
                    {getStatusLabel(delivery.status)}
                  </span>
                </div>
                <p className="text-xs mt-1" style={{ color: 'var(--color-text-tertiary)' }}>
                  {delivery.sent_at ? formatTimestamp(delivery.sent_at) : 'Not sent yet'}
                  {delivery.retry_count > 0 && ` • ${delivery.retry_count} retries`}
                </p>
                {delivery.error_msg && (
                  <p
                    className="text-xs mt-2 p-2 rounded"
                    style={{
                      backgroundColor: 'var(--color-error)' + '10',
                      color: 'var(--color-error)',
                    }}
                  >
                    {delivery.error_msg}
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
