const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: any
  ) {
    super(message);
    this.name = 'APIError';
  }
}

export async function apiClient<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    let detail;
    try {
      const error = await response.json();
      detail = error.detail || error.message;
    } catch {
      detail = response.statusText;
    }
    throw new APIError(
      detail || 'API Error',
      response.status,
      detail
    );
  }

  return response.json();
}

export { API_BASE };
