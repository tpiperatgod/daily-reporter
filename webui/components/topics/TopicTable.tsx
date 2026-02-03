'use client';

import { useState } from 'react';
import { getTopics, updateTopic, deleteTopic, triggerTopic } from '@/lib/api/topics';
import { useApi } from '@/lib/hooks/useApi';
import { cronToHuman } from '@/lib/utils/cron';
import { truncate } from '@/lib/utils/format';
import type { Topic } from '@/lib/types';

interface TopicTableProps {
  onEdit: (topic: Topic) => void;
}

export function TopicTable({ onEdit }: TopicTableProps) {
  const { data, error, mutate } = useApi<Topic[]>('/topics', { fetcher: getTopics });
  const [loading, setLoading] = useState<string | null>(null);

  const handleToggle = async (topic: Topic) => {
    setLoading(topic.id);
    try {
      await updateTopic(topic.id, { is_enabled: !topic.is_enabled });
      await mutate();
    } catch (error) {
      alert(`Failed to toggle topic: ${error}`);
    } finally {
      setLoading(null);
    }
  };

  const handleTrigger = async (topicId: string) => {
    setLoading(topicId);
    try {
      const result = await triggerTopic(topicId);
      alert(`Task started: ${result.task_id}`);
    } catch (error) {
      alert(`Failed to trigger: ${error}`);
    } finally {
      setLoading(null);
    }
  };

  const handleDelete = async (topicId: string, topicName: string) => {
    if (!confirm(`Delete topic "${topicName}"?`)) return;

    setLoading(topicId);
    try {
      await deleteTopic(topicId);
      await mutate();
    } catch (error) {
      alert(`Failed to delete: ${error}`);
    } finally {
      setLoading(null);
    }
  };

  if (error) {
    return (
      <div
        className="p-4 rounded-lg"
        style={{
          backgroundColor: 'var(--md-color-surface)',
          border: 'var(--md-border-default) solid var(--md-color-coral)',
          boxShadow: 'var(--md-shadow-card)',
        }}
      >
        <p style={{ color: 'var(--md-color-coral)' }}>Failed to load topics: {error.message}</p>
      </div>
    );
  }

  if (!data) {
    return <div>Loading topics...</div>;
  }

  return (
    <div
      className="rounded-lg overflow-hidden"
      style={{
        backgroundColor: 'var(--md-color-surface)',
        border: 'var(--md-border-default) solid var(--md-color-border)',
        boxShadow: 'var(--md-shadow-card)',
      }}
    >
      <table className="w-full">
        <thead style={{ backgroundColor: 'var(--md-color-surface-alt)' }}>
          <tr>
            <th className="text-left p-4" style={{ color: 'var(--md-color-text-primary)', fontWeight: 'var(--md-font-weight-semibold)' }}>Name</th>
            <th className="text-left p-4" style={{ color: 'var(--md-color-text-primary)', fontWeight: 'var(--md-font-weight-semibold)' }}>Query</th>
            <th className="text-left p-4" style={{ color: 'var(--md-color-text-primary)', fontWeight: 'var(--md-font-weight-semibold)' }}>Schedule</th>
            <th className="text-left p-4" style={{ color: 'var(--md-color-text-primary)', fontWeight: 'var(--md-font-weight-semibold)' }}>Status</th>
            <th className="text-left p-4" style={{ color: 'var(--md-color-text-primary)', fontWeight: 'var(--md-font-weight-semibold)' }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {data.map((topic) => (
            <tr
              key={topic.id}
              className="transition-all"
              style={{
                borderTop: 'var(--md-border-thin) solid var(--md-color-border)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--md-color-feature-light-blue)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent';
              }}
            >
              <td className="p-4">
                <button
                  onClick={() => onEdit(topic)}
                  className="font-medium hover:underline transition-colors"
                  style={{
                    color: 'var(--md-color-primary-blue)',
                    fontWeight: 'var(--md-font-weight-semibold)',
                    fontSize: 'var(--md-font-size-body)',
                  }}
                >
                  {topic.name}
                </button>
              </td>
              <td className="p-4">
                <span
                  title={topic.query}
                  className="font-mono"
                  style={{
                    color: 'var(--md-color-text-secondary)',
                    fontSize: '14px',
                  }}
                >
                  {truncate(topic.query, 50)}
                </span>
              </td>
              <td className="p-4">
                <span
                  style={{
                    color: 'var(--md-color-text-primary)',
                    fontSize: '14px',
                  }}
                >
                  {cronToHuman(topic.cron_expression)}
                </span>
              </td>
              <td className="p-4">
                <button
                  onClick={() => handleToggle(topic)}
                  disabled={loading === topic.id}
                  className="px-4 py-2 rounded-lg text-sm font-medium transition-all"
                  style={{
                    backgroundColor: topic.is_enabled ? 'var(--md-color-green)' : 'var(--md-color-surface-alt)',
                    color: topic.is_enabled ? 'white' : 'var(--md-color-text-secondary)',
                    border: 'var(--md-border-default) solid var(--md-color-border)',
                    boxShadow: 'var(--md-shadow-button)',
                    fontWeight: 'var(--md-font-weight-semibold)',
                  }}
                  onMouseEnter={(e) => {
                    if (loading !== topic.id) {
                      e.currentTarget.style.boxShadow = 'var(--md-shadow-button-hover)';
                      e.currentTarget.style.transform = 'var(--md-hover-transform)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.boxShadow = 'var(--md-shadow-button)';
                    e.currentTarget.style.transform = 'none';
                  }}
                >
                  {topic.is_enabled ? 'Enabled' : 'Disabled'}
                </button>
              </td>
              <td className="p-4">
                <div className="flex gap-2">
                  <button
                    onClick={() => handleTrigger(topic.id)}
                    disabled={loading === topic.id}
                    className="px-3 py-1 rounded text-sm transition-all"
                    style={{
                      backgroundColor: 'var(--md-color-primary-blue)',
                      color: 'white',
                      border: 'var(--md-border-default) solid var(--md-color-border)',
                      boxShadow: 'var(--md-shadow-button)',
                    }}
                    title="Trigger Now"
                    onMouseEnter={(e) => {
                      if (loading !== topic.id) {
                        e.currentTarget.style.boxShadow = 'var(--md-shadow-button-hover)';
                        e.currentTarget.style.transform = 'var(--md-hover-transform)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.boxShadow = 'var(--md-shadow-button)';
                      e.currentTarget.style.transform = 'none';
                    }}
                  >
                    ⚡
                  </button>
                  <button
                    onClick={() => onEdit(topic)}
                    className="px-3 py-1 rounded text-sm transition-all"
                    style={{
                      backgroundColor: 'var(--md-color-surface-alt)',
                      color: 'var(--md-color-text-primary)',
                      border: 'var(--md-border-default) solid var(--md-color-border)',
                      boxShadow: 'var(--md-shadow-button)',
                    }}
                    title="Edit"
                    onMouseEnter={(e) => {
                      e.currentTarget.style.boxShadow = 'var(--md-shadow-button-hover)';
                      e.currentTarget.style.transform = 'var(--md-hover-transform)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.boxShadow = 'var(--md-shadow-button)';
                      e.currentTarget.style.transform = 'none';
                    }}
                  >
                    ✏️
                  </button>
                  <button
                    onClick={() => handleDelete(topic.id, topic.name)}
                    disabled={loading === topic.id}
                    className="px-3 py-1 rounded text-sm transition-all"
                    style={{
                      backgroundColor: 'var(--md-color-coral)',
                      color: 'white',
                      border: 'var(--md-border-default) solid var(--md-color-border)',
                      boxShadow: 'var(--md-shadow-button)',
                    }}
                    title="Delete"
                    onMouseEnter={(e) => {
                      if (loading !== topic.id) {
                        e.currentTarget.style.boxShadow = 'var(--md-shadow-button-hover)';
                        e.currentTarget.style.transform = 'var(--md-hover-transform)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.boxShadow = 'var(--md-shadow-button)';
                      e.currentTarget.style.transform = 'none';
                    }}
                  >
                    🗑️
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
