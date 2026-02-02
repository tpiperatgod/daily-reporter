import React from 'react';
import { tokens } from '../tokens';

export interface IconProps extends React.HTMLAttributes<HTMLSpanElement> {
  name: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  color?: string;
}

export const Icon: React.FC<IconProps> = ({
  name,
  size = 'md',
  color,
  style,
  ...props
}) => {
  const sizes = {
    sm: '16px',
    md: '20px',
    lg: '24px',
    xl: '32px',
  };

  const iconStyles: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: sizes[size],
    color: color || tokens.colors.base.textPrimary,
    lineHeight: 1,
    userSelect: 'none',
    ...style,
  };

  // Simple emoji/symbol icon mapping
  const iconMap: Record<string, string> = {
    // Navigation
    home: '🏠',
    menu: '☰',
    close: '✕',
    back: '←',
    forward: '→',
    up: '↑',
    down: '↓',

    // Actions
    check: '✓',
    plus: '+',
    minus: '−',
    search: '🔍',
    settings: '⚙',
    edit: '✎',
    delete: '🗑',
    save: '💾',

    // Communication
    mail: '✉',
    phone: '☎',
    message: '💬',
    notification: '🔔',

    // Media
    image: '🖼',
    video: '🎥',
    music: '🎵',
    camera: '📷',

    // Common
    info: 'ℹ',
    warning: '⚠',
    error: '✖',
    success: '✓',
    help: '?',
    star: '⭐',
    heart: '❤',
    user: '👤',
    calendar: '📅',
    clock: '🕐',
    location: '📍',
    link: '🔗',

    // Arrows
    arrowLeft: '←',
    arrowRight: '→',
    arrowUp: '↑',
    arrowDown: '↓',
    chevronLeft: '‹',
    chevronRight: '›',
    chevronUp: '⌃',
    chevronDown: '⌄',
  };

  return (
    <span {...props} style={iconStyles} aria-label={name}>
      {iconMap[name] || name[0]?.toUpperCase() || '?'}
    </span>
  );
};
