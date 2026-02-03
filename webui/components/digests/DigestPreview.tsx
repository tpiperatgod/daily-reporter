'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { DeliveryTimeline } from './DeliveryTimeline';
import { getDigestContent, getUsers, sendDigest } from '@/lib/api/digests';
import { useApi } from '@/lib/hooks/useApi';
import type { Digest, User } from '@/lib/types';

interface DigestPreviewProps {
  digest: Digest;
}

export function DigestPreview({ digest }: DigestPreviewProps) {
  const [activeTab, setActiveTab] = useState<'content' | 'delivery' | 'send'>('content');
  const [selectedUserIds, setSelectedUserIds] = useState<string[]>([]);
  const [sending, setSending] = useState(false);

  const { data: content } = useApi<{ content: string }>(`/digests/${digest.id}/content`, {
    fetcher: () => getDigestContent(digest.id),
  });

  const { data: users } = useApi<User[]>('/users', {
    fetcher: () => getUsers() as any,
  });

  const handleSend = async () => {
    if (selectedUserIds.length === 0) {
      alert('Please select at least one user');
      return;
    }

    setSending(true);
    try {
      const result = await sendDigest(digest.id, { user_ids: selectedUserIds });
      alert(`Sending started! Task ID: ${result.task_id}`);
      setSelectedUserIds([]);
      setActiveTab('delivery');
    } catch (error: any) {
      alert(`Failed to send: ${error.message}`);
    } finally {
      setSending(false);
    }
  };

  const tabs = [
    { id: 'content', label: 'Content' },
    { id: 'delivery', label: 'Delivery Status' },
    { id: 'send', label: 'Manual Send' },
  ] as const;

  return (
    <div
      className="rounded-lg"
      style={{
        backgroundColor: 'var(--color-surface)',
        height: 'calc(100vh - 4rem)',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div
        className="flex border-b"
        style={{ borderColor: 'var(--color-border)' }}
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className="px-6 py-3 font-medium"
            style={{
              borderBottom:
                activeTab === tab.id ? '2px solid var(--color-primary)' : '2px solid transparent',
              color: activeTab === tab.id ? 'var(--color-primary)' : 'var(--color-text-secondary)',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === 'content' && (
          <div className="prose max-w-none">
            <ReactMarkdown
              components={{
                code({ node, inline, className, children, ...props }: any) {
                  const match = /language-(\w+)/.exec(className || '');
                  return !inline && match ? (
                    <SyntaxHighlighter
                      style={vscDarkPlus}
                      language={match[1]}
                      PreTag="div"
                      {...props}
                    >
                      {String(children).replace(/\n$/, '')}
                    </SyntaxHighlighter>
                  ) : (
                    <code className={className} {...props}>
                      {children}
                    </code>
                  );
                },
              }}
            >
              {content?.content || digest.rendered_content || 'No content available'}
            </ReactMarkdown>
          </div>
        )}

        {activeTab === 'delivery' && <DeliveryTimeline digestId={digest.id} />}

        {activeTab === 'send' && (
          <div>
            <h3 className="text-xl font-bold mb-4">Select Recipients</h3>
            <div className="space-y-2 mb-6">
              {users?.map((user) => (
                <label
                  key={user.id}
                  className="flex items-center gap-3 p-3 rounded-lg cursor-pointer"
                  style={{ backgroundColor: 'var(--color-surface-elevated)' }}
                >
                  <input
                    type="checkbox"
                    checked={selectedUserIds.includes(user.id)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedUserIds([...selectedUserIds, user.id]);
                      } else {
                        setSelectedUserIds(selectedUserIds.filter((id) => id !== user.id));
                      }
                    }}
                  />
                  <div>
                    <p className="font-medium">{user.name || user.email}</p>
                    <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                      {user.email}
                    </p>
                  </div>
                </label>
              ))}
            </div>

            <button
              onClick={handleSend}
              disabled={sending || selectedUserIds.length === 0}
              className="w-full p-4 rounded-lg font-medium"
              style={{
                backgroundColor: 'var(--color-primary)',
                color: 'white',
                opacity: sending || selectedUserIds.length === 0 ? 0.5 : 1,
              }}
            >
              {sending ? 'Sending...' : `Send to ${selectedUserIds.length} users`}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
