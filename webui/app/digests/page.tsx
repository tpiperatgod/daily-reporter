'use client';

import { useState } from 'react';
import { DigestInbox } from '@/components/digests/DigestInbox';
import { DigestPreview } from '@/components/digests/DigestPreview';
import type { Digest } from '@/lib/types';

export default function DigestsPage() {
  const [selectedDigest, setSelectedDigest] = useState<Digest | null>(null);

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Digest Archive</h1>

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
                backgroundColor: 'var(--color-surface)',
                height: 'calc(100vh - 4rem)',
              }}
            >
              <p style={{ color: 'var(--color-text-secondary)' }}>
                Select a digest to preview
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
