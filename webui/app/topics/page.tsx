'use client';

import { useState } from 'react';
import { TopicTable } from '@/components/topics/TopicTable';
import { TopicDrawer } from '@/components/topics/TopicDrawer';
import type { Topic } from '@/lib/types';

export default function TopicsPage() {
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleCreate = () => {
    setSelectedTopic(null);
    setIsDrawerOpen(true);
  };

  const handleEdit = (topic: Topic) => {
    setSelectedTopic(topic);
    setIsDrawerOpen(true);
  };

  const handleSave = () => {
    setRefreshKey((prev) => prev + 1);
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1
          style={{
            fontSize: 'var(--md-font-size-h2)',
            fontWeight: 'var(--md-font-weight-bold)',
            color: 'var(--md-color-text-primary)',
          }}
        >
          Topic Studio
        </h1>
        <button
          onClick={handleCreate}
          className="px-6 py-3 rounded-lg font-medium transition-all"
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
          + Create Topic
        </button>
      </div>

      <TopicTable key={refreshKey} onEdit={handleEdit} />

      <TopicDrawer
        topic={selectedTopic}
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        onSave={handleSave}
      />
    </div>
  );
}
