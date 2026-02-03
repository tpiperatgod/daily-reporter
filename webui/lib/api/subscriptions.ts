import { apiClient } from './client';
import type { Subscription } from '../types';

export async function getSubscriptions(): Promise<Subscription[]> {
  return apiClient<Subscription[]>('/api/v1/subscriptions');
}

export async function createSubscription(data: {
  user_id: string;
  topic_id: string;
  enable_feishu?: boolean;
  enable_email?: boolean;
}): Promise<Subscription> {
  return apiClient<Subscription>('/api/v1/subscriptions', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateSubscription(
  id: string,
  data: Partial<Subscription>
): Promise<Subscription> {
  return apiClient<Subscription>(`/api/v1/subscriptions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function deleteSubscription(id: string): Promise<void> {
  return apiClient<void>(`/api/v1/subscriptions/${id}`, {
    method: 'DELETE',
  });
}
