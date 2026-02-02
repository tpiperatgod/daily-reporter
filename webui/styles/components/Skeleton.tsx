import React from 'react';
import { tokens } from '../tokens';

export interface SkeletonProps {
  variant?: 'text' | 'circular' | 'rectangular' | 'rounded';
  width?: string | number;
  height?: string | number;
  count?: number;
  style?: React.CSSProperties;
}

interface SkeletonAvatarProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

const SkeletonComponent: React.FC<SkeletonProps> = ({
  variant = 'text',
  width,
  height,
  count = 1,
  style,
}) => {
  const baseStyles: React.CSSProperties = {
    backgroundColor: tokens.colors.base.surface,
    border: `${tokens.borderWidth.default} solid ${tokens.colors.base.border}`,
    position: 'relative',
    overflow: 'hidden',
    animation: 'pulse 1.5s ease-in-out infinite',
  };

  const variantStyles: Record<string, React.CSSProperties> = {
    text: {
      width: width || '100%',
      height: height || '16px',
      borderRadius: tokens.borderRadius.sm,
    },
    circular: {
      width: width || '40px',
      height: height || '40px',
      borderRadius: '50%',
    },
    rectangular: {
      width: width || '100%',
      height: height || '100px',
      borderRadius: tokens.borderRadius.sm,
    },
    rounded: {
      width: width || '100%',
      height: height || '100px',
      borderRadius: tokens.borderRadius.md,
    },
  };

  const containerStyles: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.gap.sm,
  };

  const skeletonStyles: React.CSSProperties = {
    ...baseStyles,
    ...variantStyles[variant],
    ...style,
  };

  const shimmerStyles: React.CSSProperties = {
    position: 'absolute',
    top: 0,
    left: '-100%',
    width: '100%',
    height: '100%',
    background: `linear-gradient(90deg, transparent, ${tokens.colors.base.background}, transparent)`,
    animation: 'shimmer 2s infinite',
  };

  const skeletons = Array.from({ length: count }, (_, index) => (
    <div key={index} style={skeletonStyles}>
      <div style={shimmerStyles} />
    </div>
  ));

  return (
    <>
      <style>{`
        @keyframes pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.7;
          }
        }
        @keyframes shimmer {
          0% {
            left: -100%;
          }
          100% {
            left: 100%;
          }
        }
      `}</style>
      {count > 1 ? <div style={containerStyles}>{skeletons}</div> : skeletons[0]}
    </>
  );
};

// Skeleton Avatar subcomponent
const SkeletonAvatar: React.FC<SkeletonAvatarProps> = ({ size = 'md' }) => {
  const sizes = {
    sm: 32,
    md: 40,
    lg: 56,
    xl: 80,
  };

  const avatarSize = sizes[size];

  const avatarStyles: React.CSSProperties = {
    width: `${avatarSize}px`,
    height: `${avatarSize}px`,
    borderRadius: '50%',
    backgroundColor: tokens.colors.base.surface,
    border: `${tokens.borderWidth.default} solid ${tokens.colors.base.border}`,
    position: 'relative',
    overflow: 'hidden',
    animation: 'pulse 1.5s ease-in-out infinite',
  };

  const shimmerStyles: React.CSSProperties = {
    position: 'absolute',
    top: 0,
    left: '-100%',
    width: '100%',
    height: '100%',
    background: `linear-gradient(90deg, transparent, ${tokens.colors.base.background}, transparent)`,
    animation: 'shimmer 2s infinite',
  };

  return (
    <>
      <style>{`
        @keyframes pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.7;
          }
        }
        @keyframes shimmer {
          0% {
            left: -100%;
          }
          100% {
            left: 100%;
          }
        }
      `}</style>
      <div style={avatarStyles}>
        <div style={shimmerStyles} />
      </div>
    </>
  );
};

export const Skeleton = Object.assign(SkeletonComponent, {
  Avatar: SkeletonAvatar,
});
