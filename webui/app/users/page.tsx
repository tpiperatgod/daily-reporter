'use client';

import { useState } from 'react';
import { getUsers } from '@/lib/api/users';
import { useApi } from '@/lib/hooks/useApi';
import { UserList } from '@/components/users/UserList';
import { UserDetail } from '@/components/users/UserDetail';
import { SubscriptionMatrix } from '@/components/users/SubscriptionMatrix';
import type { User } from '@/lib/types';

export default function UsersPage() {
  const { data: users, error, mutate } = useApi<User[]>('/users', { fetcher: getUsers });
  const [selectedUser, setSelectedUser] = useState<User | null>(null);

  const handleSelectUser = (user: User) => {
    setSelectedUser(user);
  };

  const handleUpdate = async () => {
    await mutate();
    // Refresh selected user data
    if (selectedUser && users) {
      const updated = users.find((u) => u.id === selectedUser.id);
      if (updated) {
        setSelectedUser(updated);
      }
    }
  };

  if (error) {
    return (
      <div className="p-4">
        <div
          className="p-4 rounded-lg"
          style={{ backgroundColor: 'var(--color-surface)', border: '2px solid var(--color-error)' }}
        >
          <p style={{ color: 'var(--color-error)' }}>Failed to load users: {error.message}</p>
        </div>
      </div>
    );
  }

  if (!users) {
    return <div className="p-4">Loading users...</div>;
  }

  return (
    <div className="h-full flex flex-col">
      <div className="p-6 pb-4">
        <h1
          style={{
            fontSize: 'var(--md-font-size-h2)',
            fontWeight: 'var(--md-font-weight-bold)',
            color: 'var(--md-color-text-primary)',
          }}
        >
          User Nexus
        </h1>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <UserList
          users={users}
          selectedUserId={selectedUser?.id}
          onSelect={handleSelectUser}
        />

        <div className="flex-1 overflow-y-auto">
          {selectedUser ? (
            <>
              <UserDetail user={selectedUser} onUpdate={handleUpdate} />
              <div style={{ borderTop: '1px solid var(--color-border)' }}>
                <SubscriptionMatrix
                  user={selectedUser}
                  subscriptions={selectedUser.subscriptions || []}
                  onUpdate={handleUpdate}
                />
              </div>
            </>
          ) : (
            <div className="h-full flex items-center justify-center">
              <p style={{ color: 'var(--color-text-secondary)', fontSize: '18px' }}>
                Select a user to view details
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
