'use client';

import { useState } from 'react';
import { getTopics } from '@/lib/api/topics';
import { createSubscription, updateSubscription, deleteSubscription } from '@/lib/api/subscriptions';
import { useApi } from '@/lib/hooks/useApi';
import type { User, Topic, Subscription } from '@/lib/types';

interface SubscriptionMatrixProps {
  user: User;
  subscriptions: Subscription[];
  onUpdate: () => void;
}

export function SubscriptionMatrix({ user, subscriptions, onUpdate }: SubscriptionMatrixProps) {
  const { data: topics } = useApi<Topic[]>('/topics', { fetcher: getTopics });
  const [loading, setLoading] = useState<string | null>(null);
  const [showAddDropdown, setShowAddDropdown] = useState(false);

  const handleToggleChannel = async (subscription: Subscription, channel: 'feishu' | 'email') => {
    setLoading(subscription.id);
    try {
      const updates = channel === 'feishu'
        ? { enable_feishu: !subscription.enable_feishu }
        : { enable_email: !subscription.enable_email };

      await updateSubscription(subscription.id, updates);
      onUpdate();
    } catch (error) {
      alert(`Failed to update subscription: ${error}`);
    } finally {
      setLoading(null);
    }
  };

  const handleAddSubscription = async (topicId: string) => {
    setLoading(topicId);
    try {
      await createSubscription({
        user_id: user.id,
        topic_id: topicId,
        enable_feishu: false,
        enable_email: false,
      });
      setShowAddDropdown(false);
      onUpdate();
    } catch (error) {
      alert(`Failed to add subscription: ${error}`);
    } finally {
      setLoading(null);
    }
  };

  const handleDeleteSubscription = async (subscription: Subscription) => {
    if (!confirm(`Remove subscription to "${subscription.topic?.name}"?`)) return;

    setLoading(subscription.id);
    try {
      await deleteSubscription(subscription.id);
      onUpdate();
    } catch (error) {
      alert(`Failed to delete subscription: ${error}`);
    } finally {
      setLoading(null);
    }
  };

  const subscribedTopicIds = new Set(subscriptions.map((sub) => sub.topic_id));
  const availableTopics = topics?.filter((topic) => !subscribedTopicIds.has(topic.id)) || [];

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-semibold" style={{ color: 'var(--color-text-primary)' }}>
          Subscriptions
        </h3>
        {availableTopics.length > 0 && (
          <div className="relative">
            <button
              onClick={() => setShowAddDropdown(!showAddDropdown)}
              className="px-4 py-2 rounded-lg font-medium"
              style={{ backgroundColor: 'var(--color-primary)', color: 'white' }}
            >
              + Add Subscription
            </button>
            {showAddDropdown && (
              <div
                className="absolute right-0 mt-2 w-64 rounded-lg shadow-lg z-10 max-h-64 overflow-y-auto"
                style={{
                  backgroundColor: 'var(--color-surface)',
                  border: '1px solid var(--color-border)',
                }}
              >
                {availableTopics.map((topic) => (
                  <button
                    key={topic.id}
                    onClick={() => handleAddSubscription(topic.id)}
                    disabled={loading === topic.id}
                    className="w-full px-4 py-3 text-left hover:bg-opacity-50 transition-colors"
                    style={{
                      borderBottom: '1px solid var(--color-border)',
                      color: 'var(--color-text-primary)',
                    }}
                  >
                    <div className="font-medium">{topic.name}</div>
                    <div className="text-sm mt-1" style={{ color: 'var(--color-text-secondary)' }}>
                      {topic.query}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {subscriptions.length === 0 ? (
        <div
          className="rounded-lg p-8 text-center"
          style={{
            backgroundColor: 'var(--color-surface)',
            border: '1px dashed var(--color-border)',
          }}
        >
          <p style={{ color: 'var(--color-text-secondary)' }}>
            No subscriptions yet. Add one to get started!
          </p>
        </div>
      ) : (
        <div className="grid gap-4">
          {subscriptions.map((subscription) => (
            <div
              key={subscription.id}
              className="rounded-lg p-4"
              style={{
                backgroundColor: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
              }}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h4 className="font-semibold mb-1" style={{ color: 'var(--color-text-primary)' }}>
                    {subscription.topic?.name || 'Unknown Topic'}
                  </h4>
                  <p className="text-sm mb-4" style={{ color: 'var(--color-text-secondary)' }}>
                    {subscription.topic?.query}
                  </p>

                  <div className="flex gap-6">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={subscription.enable_feishu}
                        onChange={() => handleToggleChannel(subscription, 'feishu')}
                        disabled={loading === subscription.id}
                        className="w-4 h-4"
                      />
                      <span style={{ color: 'var(--color-text-primary)' }}>Feishu</span>
                    </label>

                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={subscription.enable_email}
                        onChange={() => handleToggleChannel(subscription, 'email')}
                        disabled={loading === subscription.id}
                        className="w-4 h-4"
                      />
                      <span style={{ color: 'var(--color-text-primary)' }}>Email</span>
                    </label>
                  </div>
                </div>

                <button
                  onClick={() => handleDeleteSubscription(subscription)}
                  disabled={loading === subscription.id}
                  className="px-3 py-1 rounded text-sm"
                  style={{ backgroundColor: 'var(--color-error)', color: 'white' }}
                  title="Delete Subscription"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
