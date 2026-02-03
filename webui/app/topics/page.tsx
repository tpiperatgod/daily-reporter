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
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">Topic Studio</h1>
        <button
          onClick={handleCreate}
          className="px-6 py-3 rounded-lg font-medium"
          style={{
            backgroundColor: 'var(--color-primary)',
            color: 'white',
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
