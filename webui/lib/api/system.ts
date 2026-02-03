import { apiClient } from './client';
import type { HealthStatus, Metrics, ActivityResponse } from '../types';

export async function getHealth(): Promise<HealthStatus> {
  return apiClient<HealthStatus>('/health');
}

// Mock implementation - replace with real API later
export async function getMetrics(): Promise<Metrics> {
  // TODO: Replace with real API call when backend endpoint is ready
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        digests_today: Math.floor(Math.random() * 20) + 10,
        api_calls_total: Math.floor(Math.random() * 5000) + 3000,
        delivery_success_rate: 0.95 + Math.random() * 0.05,
      });
    }, 300);
  });
}

// Mock implementation - replace with real API later
export async function getActivity(): Promise<ActivityResponse> {
  // TODO: Replace with real API call when backend endpoint is ready
  const now = Date.now();
  const messages = [
    'Topic: AI Tech - Collection Started',
    'Topic: Web3 News - Collection Completed',
    'Digest Generated: AI Tech Daily',
    'Delivery Success: user@example.com via Email',
    'Topic: Crypto Updates - Collection Started',
    'Delivery Success: John Doe via Feishu',
    'Topic: DevOps News - Collection Completed',
    'Digest Generated: Web3 Weekly',
  ];

  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        items: messages.slice(0, 20).map((msg, i) => ({
          id: `log-${i}`,
          message: msg,
          timestamp: new Date(now - i * 60000).toISOString(),
          type: Math.random() > 0.9 ? 'warning' : 'info',
        })),
      });
    }, 200);
  });
}
