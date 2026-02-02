import React from 'react';
import { tokens } from '../tokens';

export interface ProgressBarProps {
  value: number;
  max?: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  variant?: 'primary' | 'success' | 'warning' | 'danger';
  label?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  max = 100,
  size = 'md',
  showLabel = false,
  variant = 'primary',
  label,
}) => {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  const sizes = {
    sm: { height: 8 },
    md: { height: 12 },
    lg: { height: 16 },
  };

  const currentSize = sizes[size];

  const variantColors: Record<string, string> = {
    primary: tokens.colors.accent.primaryBlue,
    success: tokens.colors.accent.green,
    warning: tokens.colors.accent.yellow,
    danger: tokens.colors.accent.coral,
  };

  const containerStyles: React.CSSProperties = {
    width: '100%',
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.gap.xs,
  };

  const trackStyles: React.CSSProperties = {
    width: '100%',
    height: `${currentSize.height}px`,
    backgroundColor: tokens.colors.base.surface,
    border: `${tokens.borderWidth.default} solid ${tokens.colors.base.border}`,
    borderRadius: tokens.borderRadius.sm,
    overflow: 'hidden',
    position: 'relative',
  };

  const fillStyles: React.CSSProperties = {
    height: '100%',
    width: `${percentage}%`,
    backgroundColor: variantColors[variant],
    transition: `width ${tokens.transitions.standard}`,
  };

  const labelContainerStyles: React.CSSProperties = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  };

  const labelStyles: React.CSSProperties = {
    fontFamily: tokens.typography.fontFamily.sans,
    fontSize: tokens.typography.fontSize.small.mobile,
    fontWeight: tokens.typography.fontWeight.regular,
    color: tokens.colors.base.textPrimary,
  };

  const percentageStyles: React.CSSProperties = {
    fontFamily: tokens.typography.fontFamily.mono,
    fontSize: tokens.typography.fontSize.small.mobile,
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.base.textPrimary,
  };

  return (
    <div style={containerStyles}>
      {(label || showLabel) && (
        <div style={labelContainerStyles}>
          {label && <span style={labelStyles}>{label}</span>}
          {showLabel && <span style={percentageStyles}>{Math.round(percentage)}%</span>}
        </div>
      )}
      <div style={trackStyles}>
        <div style={fillStyles} />
      </div>
    </div>
  );
};
