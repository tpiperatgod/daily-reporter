'use client';

import { useState } from 'react';
import { getDigests, getTopics } from '@/lib/api/digests';
import { useApi } from '@/lib/hooks/useApi';
import { formatTimestamp } from '@/lib/utils/format';
import type { Digest, Topic } from '@/lib/types';

interface DigestInboxProps {
  selectedDigestId: string | null;
  onSelect: (digest: Digest) => void;
}

export function DigestInbox({ selectedDigestId, onSelect }: DigestInboxProps) {
  const [filters, setFilters] = useState({
    topic_id: '',
    start_date: '',
    end_date: '',
  });

  const { data: digests } = useApi<Digest[]>('/digests', {
    fetcher: () => getDigests(filters),
  });

  const { data: topics } = useApi<Topic[]>('/topics', { fetcher: () => getTopics() as any });

  const getSentimentColor = (sentiment: string) => {
    const colors: Record<string, string> = {
      positive: 'var(--color-success)',
      neutral: 'var(--color-primary)',
      negative: 'var(--color-error)',
    };
    return colors[sentiment] || 'var(--color-text-secondary)';
  };

  return (
    <div
      className="rounded-lg p-4"
      style={{
        backgroundColor: 'var(--color-surface)',
        height: 'calc(100vh - 4rem)',
        overflowY: 'auto',
      }}
    >
      <div className="mb-4 space-y-2">
        <select
          value={filters.topic_id}
          onChange={(e) => setFilters({ ...filters, topic_id: e.target.value })}
          className="w-full p-2 rounded"
          style={{
            backgroundColor: 'var(--color-surface-elevated)',
            border: '1px solid var(--color-border)',
          }}
        >
          <option value="">All Topics</option>
          {topics?.map((topic) => (
            <option key={topic.id} value={topic.id}>
              {topic.name}
            </option>
          ))}
        </select>

        <input
          type="date"
          value={filters.start_date}
          onChange={(e) => setFilters({ ...filters, start_date: e.target.value })}
          className="w-full p-2 rounded"
          style={{
            backgroundColor: 'var(--color-surface-elevated)',
            border: '1px solid var(--color-border)',
          }}
        />

        <input
          type="date"
          value={filters.end_date}
          onChange={(e) => setFilters({ ...filters, end_date: e.target.value })}
          className="w-full p-2 rounded"
          style={{
            backgroundColor: 'var(--color-surface-elevated)',
            border: '1px solid var(--color-border)',
          }}
        />
      </div>

      <div className="space-y-2">
        {digests?.map((digest) => {
          const sentiment = digest.summary_json?.overall_sentiment || 'neutral';
          return (
            <button
              key={digest.id}
              onClick={() => onSelect(digest)}
              className="w-full text-left p-4 rounded-lg transition-colors"
              style={{
                backgroundColor:
                  selectedDigestId === digest.id
                    ? 'var(--color-primary-light)'
                    : 'var(--color-surface-elevated)',
                borderLeft:
                  selectedDigestId === digest.id
                    ? '3px solid var(--color-primary)'
                    : '3px solid transparent',
              }}
            >
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-semibold">
                  {digest.topic?.name || 'Digest'}
                </h3>
                <span
                  className="px-2 py-1 rounded-full text-xs"
                  style={{
                    backgroundColor: getSentimentColor(sentiment) + '20',
                    color: getSentimentColor(sentiment),
                  }}
                >
                  {sentiment}
                </span>
              </div>
              <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                {formatTimestamp(digest.created_at)}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
}
