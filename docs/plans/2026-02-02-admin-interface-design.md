# X-News-Digest Admin Interface Design

**Date:** 2026-02-02
**Status:** Approved
**Implementation:** Full production build

---

## Overview

Build a high-fidelity admin interface for X-News-Digest system using Next.js 14+ with App Router. The interface follows Object-Oriented UX (OOUX) principles using Drawer, Inline Edit, and Split View patterns to minimize page transitions.

---

## Architecture

### Application Structure
- **Frontend:** Next.js 14+ with App Router, completely separate from FastAPI backend
- **Communication:** REST API only
- **Port Configuration:**
  - Frontend (Next.js): `http://localhost:3000`
  - Backend (FastAPI): `http://localhost:8000`

### Design System Integration
- Copy design system from `ui-experiments/styles/` to `webui/styles/` (no "motherduck" subdirectory)
- UI components stored in `webui/components/ui/` (Button, Card, Input, Toggle, Table, etc.)
- No "motherduck" naming in code

### Project Structure
```
webui/
├── app/                          # Next.js App Router
│   ├── layout.tsx               # Root layout with Sidebar
│   ├── page.tsx                 # Redirect to /dashboard
│   ├── dashboard/page.tsx
│   ├── topics/page.tsx
│   ├── users/page.tsx
│   └── digests/page.tsx
├── components/
│   ├── ui/                      # Generic UI components
│   ├── layout/                  # Sidebar, CommandPalette
│   ├── dashboard/
│   ├── topics/
│   ├── users/
│   └── digests/
├── lib/
│   ├── api/                     # API client modules
│   ├── hooks/                   # Custom React hooks
│   ├── utils/                   # Utility functions
│   └── types/                   # TypeScript definitions
├── styles/                      # Copied from ui-experiments
│   ├── theme.css
│   ├── tokens.ts
│   └── components/
├── package.json
├── next.config.js
├── tsconfig.json
└── .env.local
```

### Data Fetching Strategy
- **Library:** SWR for data fetching and caching
- **Dashboard:** Polling every 15s (health) and 10s (activity)
- **Other Pages:** Refresh on user actions only
- **Optimistic Updates:** Toggles update UI immediately, rollback on error

### Component Design Principles
- **Drawers:** For editing (Topic Studio)
- **Split Views:** For master-detail (User Nexus, Digest Archive)
- **Inline Editing:** Where appropriate
- **Optimistic Updates:** Instant UI feedback for toggles

### Mock Strategy
- `/api/v1/metrics` and `/api/v1/activity` mocked in frontend
- Easy to swap for real endpoints later

---

## Technical Stack

### Core Dependencies
```json
{
  "swr": "^2.x",
  "react-markdown": "^9.x",
  "react-syntax-highlighter": "^15.x",
  "cronstrue": "^2.x",
  "croner": "^8.x",
  "fuse.js": "^7.x"
}
```

### Dev Dependencies
```json
{
  "@types/react-markdown": "^8.x",
  "@types/react-syntax-highlighter": "^15.x"
}
```

### Environment Configuration
`.env.local`:
```
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

---

## Implementation Steps

### Step 1: Project Initialization
1. Create Next.js project
2. Copy design system: `ui-experiments/styles/` → `webui/styles/`
3. Install all dependencies
4. Configure environment variables
5. Setup TypeScript configuration

### Step 2: Core Infrastructure
1. Create API client (`lib/api/client.ts`)
2. Define all types (`lib/types/index.ts`)
3. Create custom hooks (`lib/hooks/`)
4. Create utility functions (`lib/utils/`)
5. Implement root layout + Sidebar
6. Create CommandPalette

### Step 3: Page Implementation (Priority Order)

#### Priority 1: Topic Studio
- Core CRUD for topic management
- TopicTable + TopicDrawer components
- API integration (`lib/api/topics.ts`)

#### Priority 2: User Nexus
- Split view: user list + detail
- SubscriptionMatrix component
- API integration (`lib/api/users.ts`, `subscriptions.ts`)

#### Priority 3: Dashboard
- SystemPulse + MetricSparklines + ActivityStream
- **Mock data** for polling
- Can be replaced with real API later

#### Priority 4: Digest Archive
- DigestInbox + DigestPreview + DeliveryTimeline
- Split view + Tab switching
- API integration (`lib/api/digests.ts`)

---

## API Client Architecture

### Base Client (`lib/api/client.ts`)
```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

async function apiClient(endpoint: string, options?: RequestInit) {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'API Error');
  }

  return response.json();
}
```

### API Modules
- `lib/api/users.ts` - User CRUD
- `lib/api/topics.ts` - Topic CRUD + trigger
- `lib/api/subscriptions.ts` - Subscription CRUD
- `lib/api/digests.ts` - Digest read + send
- `lib/api/system.ts` - **Mock** metrics and activity

### Mock Implementation Example
```typescript
// lib/api/system.ts
export async function getMetrics() {
  return {
    digests_today: 12,
    api_calls_total: 3456,
    delivery_success_rate: 0.98,
  };
}

export async function getActivity() {
  return {
    items: [
      { id: '1', message: 'Topic: AI Tech - Collection Started',
        timestamp: new Date().toISOString(), type: 'info' },
    ]
  };
}
```

---

## Custom Hooks

### usePolling Hook
```typescript
// lib/hooks/usePolling.ts
import useSWR from 'swr';

export function usePolling<T>(
  key: string,
  fetcher: () => Promise<T>,
  interval: number
) {
  return useSWR(key, fetcher, {
    refreshInterval: interval,
    revalidateOnFocus: false,
    revalidateOnReconnect: true,
  });
}
```

### useApi Hook
```typescript
// lib/hooks/useApi.ts
import useSWR from 'swr';

export function useApi<T>(endpoint: string) {
  const { data, error, mutate } = useSWR(endpoint);

  return {
    data,
    error,
    isLoading: !error && !data,
    mutate,
    create: async (payload: T) => { /* POST + optimistic update */ },
    update: async (id: string, payload: Partial<T>) => { /* PATCH + optimistic update */ },
    remove: async (id: string) => { /* DELETE + optimistic update */ },
  };
}
```

**Optimistic Update Strategy:**
- Toggle switches update UI immediately
- Rollback + Toast on API failure
- Confirmation Toast on success

---

## TypeScript Types

### Core Types (`lib/types/index.ts`)

```typescript
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

export interface Digest {
  id: string;
  topic_id: string;
  time_window_start: string;
  time_window_end: string;
  summary_json: any;
  rendered_content: string;
  created_at: string;
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

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  components: {
    database: ComponentHealth;
    redis: ComponentHealth;
    celery: ComponentHealth;
  };
}

export interface ComponentHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  message: string;
  latency_ms?: number;
}
```

---

## Shared Layout Components

### Sidebar Component
**Features:**
- Fixed position, 100vh height
- Collapsible: 240px expanded, 64px collapsed
- Mobile: Hidden, opens as overlay

**Navigation:**
```typescript
const navItems = [
  { label: 'Dashboard', icon: 'home', href: '/dashboard' },
  { label: 'Topic Studio', icon: 'settings', href: '/topics' },
  { label: 'User Nexus', icon: 'users', href: '/users' },
  { label: 'Digest Archive', icon: 'archive', href: '/digests' },
];
```

**Visual States:**
- Active: Blue border highlight
- Hover: Light blue background
- Smooth transition (200ms ease-in-out)

### CommandPalette Component
**Features:**
- Global shortcut: Cmd+K (Mac) / Ctrl+K (Windows)
- Modal with search box
- Fuzzy search with fuse.js

**Search Scope:**
- Users: email, name
- Topics: name, query
- Digests: ID, topic name

**Interactions:**
- Keyboard navigation (arrow keys)
- Enter to navigate and select
- Esc to close

---

## Page Details

### 1. Dashboard Page
**Components:**
- **SystemPulse**: 3 horizontal cards (Database/Redis/Celery status)
- **MetricSparklines**: Stats grid (digest count, API calls, success rate)
- **ActivityStream**: Sticky right panel with real-time logs

**Polling:**
- Health check: 15s
- Activity stream: 10s

**Data Source:** Mock data from `lib/api/system.ts`

### 2. Topic Studio Page
**Components:**
- **TopicTable**: Table with all topics, inline Toggle for enable/disable
- **TopicDrawer**: Slide-out form (create/edit)

**Features:**
- Real-time preview: Cron → "Next run time"
- Quick actions: ⚡ Trigger now, ✏️ Edit, 🗑️ Delete

### 3. User Nexus Page
**Layout:** Split view
- Left: User list (300px)
- Right: User detail (flex-1)

**Components:**
- **UserList**: Search + user cards
- **UserDetail**: Avatar, email, webhook config
- **SubscriptionMatrix**: Cards with Topic + dual Toggle (Feishu/Email)

**Features:**
- Instant save on toggle
- Add subscription via dropdown

### 4. Digest Archive Page
**Layout:** Split view
- Left: Inbox (400px)
- Right: Preview (flex-1)

**Components:**
- **DigestInbox**: Filters + digest list
- **DigestPreview**: 3 tabs
  - Content: Markdown rendering
  - Delivery Status: Timeline with avatars + status
  - Manual Send: Target selector + send button

**Features:**
- Retry failed deliveries
- Multi-select users for manual send

---

## Success Criteria

✅ All 4 pages render without errors
✅ Design system applied consistently
✅ All CRUD operations work
✅ Real-time polling updates Dashboard
✅ Optimistic updates for toggles
✅ Command Palette navigation
✅ Responsive design (mobile/tablet)
✅ Error states display properly
✅ Loading states use appropriate components

---

## Future Enhancements (Out of Scope)
- User authentication
- User deletion feature
- Batch operations
- Export features
