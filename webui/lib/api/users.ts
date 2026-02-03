import { apiClient } from './client';
import type { User } from '../types';

export async function getUsers(): Promise<User[]> {
  return apiClient<User[]>('/api/v1/users');
}

export async function getUser(id: string): Promise<User> {
  return apiClient<User>(`/api/v1/users/${id}`);
}

export async function createUser(data: {
  email: string;
  name?: string;
  feishu_webhook_url?: string;
  feishu_webhook_secret?: string;
}): Promise<User> {
  return apiClient<User>('/api/v1/users', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateUser(
  id: string,
  data: Partial<User>
): Promise<User> {
  return apiClient<User>(`/api/v1/users/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}
