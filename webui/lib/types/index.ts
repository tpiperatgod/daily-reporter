// Pagination Type

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

// Core Entity Types

export interface User {
  id: string;
  email: string;
  name?: string;
  feishu_webhook_url?: string;
  feishu_webhook_secret?: string;
  created_at: string;
  subscriptions?: Subscription[];
}

export interface Topic {
  id: string;
  name: string;
  query: string;
  cron_expression: string;
  is_enabled: boolean;
  last_collection_timestamp?: string;
  last_tweet_id?: string;
  created_at: string;
}

export interface Subscription {
  id: string;
  user_id: string;
  topic_id: string;
  enable_feishu: boolean;
  enable_email: boolean;
  created_at: string;
  topic?: Topic;  // Optional related data
}

export interface DigestSummary {
  headline: string;
  highlights: string[];
  themes: string[];
  overall_sentiment?: string;
}

export interface Digest {
  id: string;
  topic_id: string;
  time_window_start: string;
  time_window_end: string;
  summary_json: DigestSummary;
  rendered_content: string;
  created_at: string;
  topic?: Topic;  // Optional related data
}

export interface Delivery {
  id: string;
  digest_id: string;
  user_id: string;
  channel: 'feishu' | 'email';
  status: 'pending' | 'success' | 'failed';
  retry_count: number;
  error_msg?: string;
  sent_at?: string;
  created_at: string;
  user?: User;  // Optional related data
}

// System Health Types

export interface ComponentHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  message: string;
  latency_ms?: number;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  components: {
    database: ComponentHealth;
    redis: ComponentHealth;
    celery: ComponentHealth;
  };
}

// Metrics and Activity Types

export interface Metrics {
  digests_today: number;
  api_calls_total: number;
  delivery_success_rate: number;
}

export interface ActivityLog {
  id: string;
  message: string;
  timestamp: string;
  type: 'info' | 'warning' | 'error' | 'success';
}

export interface ActivityResponse {
  items: ActivityLog[];
}
