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
      <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--color-surface)', border: '2px solid var(--color-error)' }}>
        <p style={{ color: 'var(--color-error)' }}>Failed to load topics: {error.message}</p>
      </div>
    );
  }

  if (!data) {
    return <div>Loading topics...</div>;
  }

  return (
    <div className="rounded-lg overflow-hidden" style={{ backgroundColor: 'var(--color-surface)' }}>
      <table className="w-full">
        <thead style={{ backgroundColor: 'var(--color-surface-elevated)' }}>
          <tr>
            <th className="text-left p-4">Name</th>
            <th className="text-left p-4">Query</th>
            <th className="text-left p-4">Schedule</th>
            <th className="text-left p-4">Status</th>
            <th className="text-left p-4">Actions</th>
          </tr>
        </thead>
        <tbody>
          {data.map((topic) => (
            <tr
              key={topic.id}
              className="border-t transition-colors hover:bg-opacity-50"
              style={{ borderColor: 'var(--color-border)' }}
            >
              <td className="p-4">
                <button
                  onClick={() => onEdit(topic)}
                  className="font-medium hover:underline"
                  style={{ color: 'var(--color-primary)' }}
                >
                  {topic.name}
                </button>
              </td>
              <td className="p-4">
                <span title={topic.query} style={{ color: 'var(--color-text-secondary)' }}>
                  {truncate(topic.query, 50)}
                </span>
              </td>
              <td className="p-4">
                <span className="text-sm">{cronToHuman(topic.cron_expression)}</span>
              </td>
              <td className="p-4">
                <button
                  onClick={() => handleToggle(topic)}
                  disabled={loading === topic.id}
                  className="px-4 py-2 rounded-lg text-sm font-medium"
                  style={{
                    backgroundColor: topic.is_enabled ? 'var(--color-success)' : 'var(--color-border)',
                    color: topic.is_enabled ? 'white' : 'var(--color-text-secondary)',
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
                    className="px-3 py-1 rounded text-sm"
                    style={{ backgroundColor: 'var(--color-primary)', color: 'white' }}
                    title="Trigger Now"
                  >
                    ⚡
                  </button>
                  <button
                    onClick={() => onEdit(topic)}
                    className="px-3 py-1 rounded text-sm"
                    style={{ backgroundColor: 'var(--color-surface-elevated)' }}
                    title="Edit"
                  >
                    ✏️
                  </button>
                  <button
                    onClick={() => handleDelete(topic.id, topic.name)}
                    disabled={loading === topic.id}
                    className="px-3 py-1 rounded text-sm"
                    style={{ backgroundColor: 'var(--color-error)', color: 'white' }}
                    title="Delete"
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
