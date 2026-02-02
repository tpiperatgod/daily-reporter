import React from 'react';
import { tokens } from '../tokens';

export interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'default' | 'dots' | 'bars';
  color?: string;
  label?: string;
}

export const Spinner: React.FC<SpinnerProps> = ({
  size = 'md',
  variant = 'default',
  color,
  label,
}) => {
  const sizes = {
    sm: 16,
    md: 32,
    lg: 48,
    xl: 64,
  };

  const dotSizes = {
    sm: 6,
    md: 8,
    lg: 10,
    xl: 12,
  };

  const barWidths = {
    sm: 4,
    md: 6,
    lg: 8,
    xl: 10,
  };

  const barHeights = {
    sm: 16,
    md: 24,
    lg: 32,
    xl: 48,
  };

  const spinnerSize = sizes[size];
  const dotSize = dotSizes[size];
  const barWidth = barWidths[size];
  const barHeight = barHeights[size];
  const spinnerColor = color || tokens.colors.accent.primaryBlue;

  const containerStyles: React.CSSProperties = {
    display: 'inline-flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: tokens.gap.md,
  };

  const labelStyles: React.CSSProperties = {
    fontFamily: tokens.typography.fontFamily.sans,
    fontSize: tokens.typography.fontSize.small.mobile,
    fontWeight: tokens.typography.fontWeight.regular,
    color: tokens.colors.base.textPrimary,
  };

  // Dots variant
  if (variant === 'dots') {
    const dotsContainerStyles: React.CSSProperties = {
      display: 'flex',
      alignItems: 'center',
      gap: '4px',
    };

    const dotStyles: React.CSSProperties = {
      width: `${dotSize}px`,
      height: `${dotSize}px`,
      borderRadius: '50%',
      backgroundColor: spinnerColor,
      animation: 'bounce 1s ease-in-out infinite',
    };

    return (
      <>
        <style>{`
          @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
          }
        `}</style>
        <div style={containerStyles}>
          <div style={dotsContainerStyles} role="status" aria-label={label || 'Loading'}>
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                style={{
                  ...dotStyles,
                  animationDelay: `${i * 0.1}s`,
                }}
              />
            ))}
          </div>
          {label && <span style={labelStyles}>{label}</span>}
        </div>
      </>
    );
  }

  // Bars variant
  if (variant === 'bars') {
    const barsContainerStyles: React.CSSProperties = {
      display: 'flex',
      alignItems: 'flex-end',
      gap: '4px',
      height: `${barHeight}px`,
    };

    const barStyles: React.CSSProperties = {
      width: `${barWidth}px`,
      backgroundColor: spinnerColor,
      borderRadius: tokens.borderRadius.sm,
      animation: 'bars 1s ease-in-out infinite',
    };

    return (
      <>
        <style>{`
          @keyframes bars {
            0%, 100% { height: 30%; }
            50% { height: 100%; }
          }
        `}</style>
        <div style={containerStyles}>
          <div style={barsContainerStyles} role="status" aria-label={label || 'Loading'}>
            {[0, 1, 2, 3].map((i) => (
              <span
                key={i}
                style={{
                  ...barStyles,
                  animationDelay: `${i * 0.1}s`,
                }}
              />
            ))}
          </div>
          {label && <span style={labelStyles}>{label}</span>}
        </div>
      </>
    );
  }

  // Default variant (spinning circle)
  const spinnerStyles: React.CSSProperties = {
    width: `${spinnerSize}px`,
    height: `${spinnerSize}px`,
    border: `${tokens.borderWidth.default} solid ${tokens.colors.base.border}`,
    borderTopColor: spinnerColor,
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  };

  return (
    <>
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
      <div style={containerStyles}>
        <div style={spinnerStyles} role="status" aria-label={label || 'Loading'} />
        {label && <span style={labelStyles}>{label}</span>}
      </div>
    </>
  );
};
