'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Fuse from 'fuse.js';
import { getUsers } from '@/lib/api/users';
import { getTopics } from '@/lib/api/topics';
import { getDigests } from '@/lib/api/digests';

interface SearchItem {
  id: string;
  title: string;
  subtitle: string;
  href: string;
  type: 'user' | 'topic' | 'digest';
}

export function CommandPalette() {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [items, setItems] = useState<SearchItem[]>([]);
  const [fuse, setFuse] = useState<Fuse<SearchItem> | null>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(true);
      }
      if (e.key === 'Escape') {
        setIsOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    if (isOpen && items.length === 0) {
      loadItems();
    }
  }, [isOpen]);

  const loadItems = async () => {
    try {
      const [users, topics, digests] = await Promise.all([
        getUsers() as any,
        getTopics() as any,
        getDigests() as any,
      ]);

      const searchItems: SearchItem[] = [
        ...users.map((u: any) => ({
          id: u.id,
          title: u.name || u.email,
          subtitle: u.email,
          href: `/users?id=${u.id}`,
          type: 'user' as const,
        })),
        ...topics.map((t: any) => ({
          id: t.id,
          title: t.name,
          subtitle: t.query,
          href: `/topics?id=${t.id}`,
          type: 'topic' as const,
        })),
        ...digests.slice(0, 20).map((d: any) => ({
          id: d.id,
          title: d.topic?.name || 'Digest',
          subtitle: d.id,
          href: `/digests?id=${d.id}`,
          type: 'digest' as const,
        })),
      ];

      setItems(searchItems);
      setFuse(
        new Fuse(searchItems, {
          keys: ['title', 'subtitle'],
          threshold: 0.3,
        })
      );
    } catch (error) {
      console.error('Failed to load search items:', error);
    }
  };

  const results = search && fuse
    ? fuse.search(search).map((r) => r.item)
    : items.slice(0, 10);

  const handleSelect = (href: string) => {
    router.push(href);
    setIsOpen(false);
    setSearch('');
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-20"
      style={{ backgroundColor: 'var(--color-overlay)' }}
      onClick={() => setIsOpen(false)}
    >
      <div
        className="rounded-lg w-full max-w-2xl"
        style={{
          backgroundColor: 'var(--md-color-surface)',
          border: 'var(--md-border-default) solid var(--md-color-border)',
          boxShadow: 'var(--md-shadow-card-elevated)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <input
          type="text"
          placeholder="Search users, topics, digests..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          autoFocus
          className="w-full p-4 text-lg rounded-t-lg"
          style={{
            backgroundColor: 'var(--md-color-background)',
            border: 'none',
            outline: 'none',
            color: 'var(--md-color-text-primary)',
          }}
        />

        <div className="max-h-96 overflow-y-auto" style={{ borderTop: 'var(--md-border-thin) solid var(--md-color-border)' }}>
          {results.map((item, index) => (
            <button
              key={item.id}
              onClick={() => handleSelect(item.href)}
              className="w-full text-left p-4 hover:bg-opacity-50 transition-colors"
              style={{
                backgroundColor:
                  index === 0 ? 'var(--md-color-feature-light-blue)' : 'transparent',
                borderBottom: 'var(--md-border-thin) solid var(--md-color-border)',
              }}
            >
              <p className="font-medium" style={{ color: 'var(--md-color-text-primary)' }}>{item.title}</p>
              <p className="text-sm" style={{ color: 'var(--md-color-text-secondary)' }}>
                {item.subtitle}
              </p>
            </button>
          ))}
        </div>

        <div
          className="p-3 text-sm text-center"
          style={{
            color: 'var(--md-color-text-secondary)',
            borderTop: 'var(--md-border-thin) solid var(--md-color-border)',
          }}
        >
          Press <kbd style={{ color: 'var(--md-color-text-primary)' }}>Esc</kbd> to close
        </div>
      </div>
    </div>
  );
}
