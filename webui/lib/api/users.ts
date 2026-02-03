import { apiClient } from './client';
import type { User, PaginatedResponse } from '../types';

export async function getUsers(): Promise<User[]> {
  const response = await apiClient<PaginatedResponse<User>>('/api/v1/users');
  return response.items;
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

export async function deleteUser(id: string): Promise<void> {
  return apiClient<void>(`/api/v1/users/${id}`, {
    method: 'DELETE',
  });
}
