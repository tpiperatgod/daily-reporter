'use client';

import { useState } from 'react';
import { DigestInbox } from '@/components/digests/DigestInbox';
import { DigestPreview } from '@/components/digests/DigestPreview';
import type { Digest } from '@/lib/types';

export default function DigestsPage() {
  const [selectedDigest, setSelectedDigest] = useState<Digest | null>(null);

  return (
    <div className="p-6">
      <h1
        className="mb-6"
        style={{
          fontSize: 'var(--md-font-size-h2)',
          fontWeight: 'var(--md-font-weight-bold)',
          color: 'var(--md-color-text-primary)',
        }}
      >
        Digest Archive
      </h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <DigestInbox
            selectedDigestId={selectedDigest?.id || null}
            onSelect={setSelectedDigest}
          />
        </div>
        <div className="lg:col-span-2">
          {selectedDigest ? (
            <DigestPreview digest={selectedDigest} />
          ) : (
            <div
              className="rounded-lg p-6 flex items-center justify-center"
              style={{
                backgroundColor: 'var(--md-color-surface)',
                border: 'var(--md-border-default) solid var(--md-color-border)',
                boxShadow: 'var(--md-shadow-card)',
                height: 'calc(100vh - 4rem)',
              }}
            >
              <p style={{ color: 'var(--md-color-text-secondary)', fontSize: '18px' }}>
                Select a digest to preview
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
