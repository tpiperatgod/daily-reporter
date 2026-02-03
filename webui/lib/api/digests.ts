import { apiClient } from './client';
import type { Digest, Delivery } from '../types';

export async function getDigests(params?: {
  topic_id?: string;
  start_date?: string;
  end_date?: string;
}): Promise<Digest[]> {
  const query = new URLSearchParams();
  if (params?.topic_id) query.set('topic_id', params.topic_id);
  if (params?.start_date) query.set('start_date', params.start_date);
  if (params?.end_date) query.set('end_date', params.end_date);

  const queryString = query.toString();
  return apiClient<Digest[]>(`/api/v1/digests${queryString ? `?${queryString}` : ''}`);
}

export async function getDigest(id: string): Promise<Digest> {
  return apiClient<Digest>(`/api/v1/digests/${id}`);
}

export async function getDigestContent(id: string): Promise<{ content: string }> {
  return apiClient<{ content: string }>(`/api/v1/digests/${id}/content`);
}

export async function getDigestDeliveries(id: string): Promise<Delivery[]> {
  return apiClient<Delivery[]>(`/api/v1/digests/${id}/deliveries`);
}

export async function sendDigest(
  id: string,
  data: { user_ids: string[] }
): Promise<{ task_id: string }> {
  return apiClient<{ task_id: string }>(`/api/v1/digests/${id}/send`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
