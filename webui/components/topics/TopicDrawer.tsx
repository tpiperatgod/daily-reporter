'use client';

import { useState, useEffect } from 'react';
import { createTopic, updateTopic } from '@/lib/api/topics';
import { cronToHuman, formatNextRun } from '@/lib/utils/cron';
import type { Topic } from '@/lib/types';

interface TopicDrawerProps {
  topic: Topic | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: () => void;
}

export function TopicDrawer({ topic, isOpen, onClose, onSave }: TopicDrawerProps) {
  const [formData, setFormData] = useState({
    name: '',
    query: '',
    cron_expression: '',
    is_enabled: true,
  });
  const [cronPreview, setCronPreview] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (topic) {
      setFormData({
        name: topic.name,
        query: topic.query,
        cron_expression: topic.cron_expression,
        is_enabled: topic.is_enabled,
      });
    } else {
      setFormData({
        name: '',
        query: '',
        cron_expression: '',
        is_enabled: true,
      });
    }
  }, [topic]);

  useEffect(() => {
    if (formData.cron_expression) {
      try {
        const human = cronToHuman(formData.cron_expression);
        const next = formatNextRun(formData.cron_expression);
        setCronPreview(`${human} • Next run: ${next}`);
      } catch {
        setCronPreview('Invalid cron expression');
      }
    } else {
      setCronPreview('');
    }
  }, [formData.cron_expression]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (topic) {
        await updateTopic(topic.id, formData);
      } else {
        await createTopic(formData);
      }
      onSave();
      onClose();
    } catch (error: any) {
      alert(`Failed to save: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ backgroundColor: 'var(--color-overlay)' }}
      onClick={onClose}
    >
      <div
        className="rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        style={{
          backgroundColor: 'var(--md-color-surface)',
          border: 'var(--md-border-default) solid var(--md-color-border)',
          boxShadow: 'var(--md-shadow-card-elevated)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-2xl font-bold mb-6" style={{ color: 'var(--md-color-text-primary)' }}>
          {topic ? 'Edit Topic' : 'Create Topic'}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block mb-2 font-medium" style={{ color: 'var(--md-color-text-secondary)' }}>Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              className="w-full p-3 rounded-lg"
              style={{
                backgroundColor: 'var(--md-color-background)',
                border: 'var(--md-border-default) solid var(--md-color-border)',
                color: 'var(--md-color-text-primary)',
              }}
            />
          </div>

          <div>
            <label className="block mb-2 font-medium" style={{ color: 'var(--md-color-text-secondary)' }}>Query</label>
            <textarea
              value={formData.query}
              onChange={(e) => setFormData({ ...formData, query: e.target.value })}
              required
              rows={4}
              className="w-full p-3 rounded-lg font-mono text-sm"
              style={{
                backgroundColor: 'var(--md-color-background)',
                border: 'var(--md-border-default) solid var(--md-color-border)',
                color: 'var(--md-color-text-primary)',
              }}
            />
          </div>

          <div>
            <label className="block mb-2 font-medium" style={{ color: 'var(--md-color-text-secondary)' }}>Cron Expression</label>
            <input
              type="text"
              value={formData.cron_expression}
              onChange={(e) => setFormData({ ...formData, cron_expression: e.target.value })}
              required
              placeholder="0 9 * * *"
              className="w-full p-3 rounded-lg font-mono"
              style={{
                backgroundColor: 'var(--md-color-background)',
                border: 'var(--md-border-default) solid var(--md-color-border)',
                color: 'var(--md-color-text-primary)',
              }}
            />
            {cronPreview && (
              <p
                className="text-sm mt-2"
                style={{
                  color: cronPreview.includes('Invalid')
                    ? 'var(--md-color-coral)'
                    : 'var(--md-color-text-secondary)',
                }}
              >
                {cronPreview}
              </p>
            )}
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={formData.is_enabled}
              onChange={(e) => setFormData({ ...formData, is_enabled: e.target.checked })}
              id="is_enabled"
            />
            <label htmlFor="is_enabled" style={{ color: 'var(--md-color-text-primary)' }}>Enable topic</label>
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2 rounded-lg flex-1 transition-all"
              style={{
                backgroundColor: 'var(--md-color-surface-alt)',
                border: 'var(--md-border-default) solid var(--md-color-border)',
                boxShadow: 'var(--md-shadow-button)',
                color: 'var(--md-color-text-primary)',
                fontWeight: 'var(--md-font-weight-semibold)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.boxShadow = 'var(--md-shadow-button-hover)';
                e.currentTarget.style.transform = 'var(--md-hover-transform)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.boxShadow = 'var(--md-shadow-button)';
                e.currentTarget.style.transform = 'none';
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2 rounded-lg flex-1 transition-all"
              style={{
                backgroundColor: 'var(--md-color-primary-blue)',
                color: 'var(--md-color-text-primary)',
                border: 'var(--md-border-default) solid var(--md-color-border)',
                boxShadow: 'var(--md-shadow-button)',
                fontWeight: 'var(--md-font-weight-semibold)',
              }}
              onMouseEnter={(e) => {
                if (!loading) {
                  e.currentTarget.style.boxShadow = 'var(--md-shadow-button-hover)';
                  e.currentTarget.style.transform = 'var(--md-hover-transform)';
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.boxShadow = 'var(--md-shadow-button)';
                e.currentTarget.style.transform = 'none';
              }}
            >
              {loading ? 'Saving...' : 'Save Topic'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
