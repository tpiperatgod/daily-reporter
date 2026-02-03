'use client';

import { useState } from 'react';
import { updateUser } from '@/lib/api/users';
import type { User } from '@/lib/types';
import { formatTimestamp } from '@/lib/utils/format';

interface UserDetailProps {
  user: User;
  onUpdate: () => void;
}

export function UserDetail({ user, onUpdate }: UserDetailProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState(user.name || '');
  const [webhookUrl, setWebhookUrl] = useState(user.feishu_webhook_url || '');
  const [webhookSecret, setWebhookSecret] = useState(user.feishu_webhook_secret || '');
  const [loading, setLoading] = useState(false);

  const handleSave = async () => {
    setLoading(true);
    try {
      await updateUser(user.id, {
        name: name || undefined,
        feishu_webhook_url: webhookUrl || undefined,
        feishu_webhook_secret: webhookSecret || undefined,
      });
      setIsEditing(false);
      onUpdate();
    } catch (error) {
      alert(`Failed to update user: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    setName(user.name || '');
    setWebhookUrl(user.feishu_webhook_url || '');
    setWebhookSecret(user.feishu_webhook_secret || '');
    setIsEditing(false);
  };

  return (
    <div className="p-6">
      <div className="flex items-center gap-4 mb-6">
        <div
          className="w-16 h-16 rounded-full flex items-center justify-center text-white text-2xl font-medium"
          style={{ backgroundColor: 'var(--md-color-primary-blue)' }}
        >
          {user.name?.[0]?.toUpperCase() || user.email[0].toUpperCase()}
        </div>
        <div className="flex-1">
          <h2 className="text-2xl font-bold" style={{ color: 'var(--md-color-text-primary)' }}>
            {user.name || user.email}
          </h2>
          {user.name && (
            <p style={{ color: 'var(--md-color-text-secondary)' }}>{user.email}</p>
          )}
          <p className="text-sm mt-1" style={{ color: 'var(--md-color-text-secondary)' }}>
            Created {formatTimestamp(user.created_at)}
          </p>
        </div>
        {!isEditing && (
          <button
            onClick={() => setIsEditing(true)}
            className="px-4 py-2 rounded-lg font-medium transition-all"
            style={{
              backgroundColor: 'var(--md-color-primary-blue)',
              color: 'var(--md-color-text-primary)',
              border: 'var(--md-border-default) solid var(--md-color-border)',
              boxShadow: 'var(--md-shadow-button)',
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
            Edit
          </button>
        )}
      </div>

      <div
        className="rounded-lg p-6"
        style={{
          backgroundColor: 'var(--md-color-surface)',
          border: 'var(--md-border-default) solid var(--md-color-border)',
          boxShadow: 'var(--md-shadow-card)',
        }}
      >
        <h3
          className="text-lg font-semibold mb-4"
          style={{
            color: 'var(--md-color-text-primary)',
            fontWeight: 'var(--md-font-weight-semibold)',
          }}
        >
          User Information
        </h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2" style={{ color: 'var(--md-color-text-secondary)' }}>
              Name
            </label>
            {isEditing ? (
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Enter name"
                className="w-full px-3 py-2 rounded-lg"
                style={{
                  backgroundColor: 'var(--md-color-background)',
                  border: 'var(--md-border-default) solid var(--md-color-border)',
                  color: 'var(--md-color-text-primary)',
                }}
              />
            ) : (
              <p style={{ color: 'var(--md-color-text-primary)' }}>{user.name || 'Not set'}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-2" style={{ color: 'var(--md-color-text-secondary)' }}>
              Feishu Webhook URL
            </label>
            {isEditing ? (
              <input
                type="url"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..."
                className="w-full px-3 py-2 rounded-lg font-mono text-sm"
                style={{
                  backgroundColor: 'var(--md-color-background)',
                  border: 'var(--md-border-default) solid var(--md-color-border)',
                  color: 'var(--md-color-text-primary)',
                }}
              />
            ) : (
              <p className="font-mono text-sm" style={{ color: 'var(--md-color-text-primary)' }}>
                {user.feishu_webhook_url || 'Not set'}
              </p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-2" style={{ color: 'var(--md-color-text-secondary)' }}>
              Feishu Webhook Secret
            </label>
            {isEditing ? (
              <input
                type="password"
                value={webhookSecret}
                onChange={(e) => setWebhookSecret(e.target.value)}
                placeholder="Enter webhook secret"
                className="w-full px-3 py-2 rounded-lg font-mono text-sm"
                style={{
                  backgroundColor: 'var(--md-color-background)',
                  border: 'var(--md-border-default) solid var(--md-color-border)',
                  color: 'var(--md-color-text-primary)',
                }}
              />
            ) : (
              <p className="font-mono text-sm" style={{ color: 'var(--md-color-text-primary)' }}>
                {user.feishu_webhook_secret ? '••••••••' : 'Not set'}
              </p>
            )}
          </div>
        </div>

        {isEditing && (
          <div className="flex gap-3 mt-6">
            <button
              onClick={handleSave}
              disabled={loading}
              className="px-4 py-2 rounded-lg font-medium transition-all"
              style={{
                backgroundColor: 'var(--md-color-green)',
                color: 'white',
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
              {loading ? 'Saving...' : 'Save Changes'}
            </button>
            <button
              onClick={handleCancel}
              disabled={loading}
              className="px-4 py-2 rounded-lg font-medium transition-all"
              style={{
                backgroundColor: 'var(--md-color-surface-alt)',
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
              Cancel
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
