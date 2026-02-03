'use client';

import { useState } from 'react';
import { getDigests } from '@/lib/api/digests';
import { getTopics } from '@/lib/api/topics';
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
      positive: 'var(--md-color-green)',
      neutral: 'var(--md-color-primary-blue)',
      negative: 'var(--md-color-coral)',
    };
    return colors[sentiment] || 'var(--md-color-text-secondary)';
  };

  return (
    <div
      className="rounded-lg p-4"
      style={{
        backgroundColor: 'var(--md-color-surface)',
        border: 'var(--md-border-default) solid var(--md-color-border)',
        boxShadow: 'var(--md-shadow-card)',
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
            backgroundColor: 'var(--md-color-background)',
            border: 'var(--md-border-default) solid var(--md-color-border)',
            color: 'var(--md-color-text-primary)',
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
            backgroundColor: 'var(--md-color-background)',
            border: 'var(--md-border-default) solid var(--md-color-border)',
            color: 'var(--md-color-text-primary)',
          }}
        />

        <input
          type="date"
          value={filters.end_date}
          onChange={(e) => setFilters({ ...filters, end_date: e.target.value })}
          className="w-full p-2 rounded"
          style={{
            backgroundColor: 'var(--md-color-background)',
            border: 'var(--md-border-default) solid var(--md-color-border)',
            color: 'var(--md-color-text-primary)',
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
                    ? 'var(--md-color-feature-light-blue)'
                    : 'var(--md-color-surface-alt)',
                borderLeft:
                  selectedDigestId === digest.id
                    ? 'var(--md-border-thick) solid var(--md-color-primary-blue)'
                    : 'var(--md-border-thick) solid transparent',
                borderTop: 'var(--md-border-default) solid var(--md-color-border)',
                borderRight: 'var(--md-border-default) solid var(--md-color-border)',
                borderBottom: 'var(--md-border-default) solid var(--md-color-border)',
              }}
            >
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-semibold" style={{ color: 'var(--md-color-text-primary)' }}>
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
              <p className="text-sm" style={{ color: 'var(--md-color-text-secondary)' }}>
                {formatTimestamp(digest.created_at)}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
}
