import React from 'react';
import { tokens } from '../tokens';

export interface TagProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'yellow' | 'coral' | 'blue' | 'green';
  size?: 'sm' | 'md';
  removable?: boolean;
  onRemove?: () => void;
  playful?: boolean;
  children: React.ReactNode;
}

export const Tag: React.FC<TagProps> = ({
  variant = 'yellow',
  size = 'md',
  removable = false,
  onRemove,
  playful = false,
  children,
  style,
  ...props
}) => {
  const variantStyles: Record<string, React.CSSProperties> = {
    yellow: {
      backgroundColor: tokens.colors.accent.yellow,
      color: tokens.colors.base.textPrimary,
    },
    coral: {
      backgroundColor: tokens.colors.accent.coral,
      color: tokens.colors.base.surfaceAlt,
    },
    blue: {
      backgroundColor: tokens.colors.accent.primaryBlue,
      color: tokens.colors.base.textPrimary,
    },
    green: {
      backgroundColor: tokens.colors.accent.green,
      color: tokens.colors.base.surfaceAlt,
    },
  };

  const sizeStyles: Record<string, React.CSSProperties> = {
    sm: {
      padding: `${tokens.spacing.xs} ${tokens.spacing.sm}`,
      fontSize: '11px',
    },
    md: {
      padding: `${tokens.spacing.xs} ${tokens.spacing.md}`,
      fontSize: tokens.typography.fontSize.small.mobile,
    },
  };

  const baseStyles: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: tokens.gap.xs,
    fontWeight: tokens.typography.fontWeight.semibold,
    fontFamily: tokens.typography.fontFamily.sans,
    textTransform: 'uppercase',
    letterSpacing: tokens.typography.letterSpacing.normal,
    border: `${tokens.borderWidth.default} solid ${tokens.colors.base.border}`,
    borderRadius: tokens.borderRadius.sm,
    whiteSpace: 'nowrap',
    ...sizeStyles[size],
    ...(playful && {
      transform: `rotate(${Math.random() > 0.5 ? '1deg' : '-1deg'})`,
    }),
  };

  const removeButtonStyles: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '16px',
    height: '16px',
    cursor: 'pointer',
    border: 'none',
    background: 'transparent',
    padding: 0,
    marginLeft: tokens.spacing.xs,
    color: 'inherit',
    fontSize: '12px',
    fontWeight: tokens.typography.fontWeight.bold,
    transition: `opacity ${tokens.transitions.fast}`,
  };

  return (
    <div
      {...props}
      style={{
        ...baseStyles,
        ...variantStyles[variant],
        ...style,
      }}
    >
      {children}
      {removable && (
        <button
          style={removeButtonStyles}
          onClick={(e) => {
            e.stopPropagation();
            onRemove?.();
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.opacity = '0.7';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.opacity = '1';
          }}
          aria-label="Remove tag"
        >
          ×
        </button>
      )}
    </div>
  );
};
