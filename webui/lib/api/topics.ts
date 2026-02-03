import { apiClient } from './client';
import type { Topic, PaginatedResponse } from '../types';

export async function getTopics(): Promise<Topic[]> {
  const response = await apiClient<PaginatedResponse<Topic>>('/api/v1/topics');
  return response.items;
}

export async function getTopic(id: string): Promise<Topic> {
  return apiClient<Topic>(`/api/v1/topics/${id}`);
}

export async function createTopic(data: {
  name: string;
  query: string;
  cron_expression: string;
  is_enabled?: boolean;
}): Promise<Topic> {
  return apiClient<Topic>('/api/v1/topics', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateTopic(
  id: string,
  data: Partial<Topic>
): Promise<Topic> {
  return apiClient<Topic>(`/api/v1/topics/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function deleteTopic(id: string): Promise<void> {
  return apiClient<void>(`/api/v1/topics/${id}`, {
    method: 'DELETE',
  });
}

export async function triggerTopic(id: string): Promise<{ task_id: string }> {
  return apiClient<{ task_id: string }>(`/api/v1/topics/${id}/trigger`, {
    method: 'POST',
  });
}
