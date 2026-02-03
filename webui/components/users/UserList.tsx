'use client';

import { useState } from 'react';
import type { User } from '@/lib/types';
import { formatTimestamp } from '@/lib/utils/format';

interface UserListProps {
  users: User[];
  selectedUserId?: string;
  onSelect: (user: User) => void;
}

export function UserList({ users, selectedUserId, onSelect }: UserListProps) {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredUsers = users.filter((user) => {
    const query = searchQuery.toLowerCase();
    return (
      user.email.toLowerCase().includes(query) ||
      user.name?.toLowerCase().includes(query)
    );
  });

  return (
    <div className="flex flex-col h-full" style={{ width: '300px', borderRight: '1px solid var(--color-border)' }}>
      <div className="p-4" style={{ borderBottom: '1px solid var(--color-border)' }}>
        <input
          type="text"
          placeholder="Search users..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full px-3 py-2 rounded-lg"
          style={{
            backgroundColor: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            color: 'var(--color-text-primary)',
          }}
        />
      </div>

      <div className="flex-1 overflow-y-auto">
        {filteredUsers.length === 0 ? (
          <div className="p-4 text-center" style={{ color: 'var(--color-text-secondary)' }}>
            {searchQuery ? 'No users found' : 'No users yet'}
          </div>
        ) : (
          filteredUsers.map((user) => (
            <button
              key={user.id}
              onClick={() => onSelect(user)}
              className="w-full p-4 text-left transition-colors"
              style={{
                backgroundColor: selectedUserId === user.id ? 'var(--color-surface-elevated)' : 'transparent',
                borderLeft: selectedUserId === user.id ? '3px solid var(--color-primary)' : '3px solid transparent',
                borderBottom: '1px solid var(--color-border)',
              }}
            >
              <div className="flex items-center gap-3">
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center text-white font-medium"
                  style={{ backgroundColor: 'var(--color-primary)' }}
                >
                  {user.name?.[0]?.toUpperCase() || user.email[0].toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium truncate" style={{ color: 'var(--color-text-primary)' }}>
                    {user.name || user.email}
                  </div>
                  {user.name && (
                    <div className="text-sm truncate" style={{ color: 'var(--color-text-secondary)' }}>
                      {user.email}
                    </div>
                  )}
                  <div className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
                    {formatTimestamp(user.created_at)}
                  </div>
                </div>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
