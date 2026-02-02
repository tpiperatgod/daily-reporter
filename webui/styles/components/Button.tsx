import React from 'react';
import { tokens } from '../tokens';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  fullWidth?: boolean;
  children: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  loading = false,
  fullWidth = false,
  disabled = false,
  children,
  style,
  ...props
}) => {
  const baseStyles: React.CSSProperties = {
    fontFamily: tokens.typography.fontFamily.sans,
    fontWeight: tokens.typography.fontWeight.semibold,
    border: `${tokens.borderWidth.default} solid ${tokens.colors.base.border}`,
    borderRadius: tokens.borderRadius.sm,
    cursor: disabled || loading ? 'not-allowed' : 'pointer',
    transition: `all ${tokens.transitions.fast}`,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: tokens.gap.sm,
    textTransform: 'none',
    whiteSpace: 'nowrap',
    position: 'relative',
    opacity: disabled ? 0.5 : 1,
    width: fullWidth ? '100%' : 'auto',
  };

  const sizeStyles: Record<string, React.CSSProperties> = {
    sm: {
      height: tokens.sizes.button.sm.height,
      padding: tokens.sizes.button.sm.padding,
      fontSize: tokens.sizes.button.sm.fontSize,
    },
    md: {
      height: tokens.sizes.button.md.height,
      padding: tokens.sizes.button.md.padding,
      fontSize: tokens.sizes.button.md.fontSize,
    },
    lg: {
      height: tokens.sizes.button.lg.height,
      padding: tokens.sizes.button.lg.padding,
      fontSize: tokens.sizes.button.lg.fontSize,
    },
  };

  const variantStyles: Record<string, React.CSSProperties> = {
    primary: {
      backgroundColor: tokens.colors.accent.primaryBlue,
      color: tokens.colors.base.textPrimary,
      boxShadow: tokens.shadows.button,
    },
    secondary: {
      backgroundColor: tokens.colors.base.surfaceAlt,
      color: tokens.colors.base.textPrimary,
      boxShadow: tokens.shadows.button,
    },
    ghost: {
      backgroundColor: 'transparent',
      color: tokens.colors.base.textPrimary,
      boxShadow: 'none',
    },
    danger: {
      backgroundColor: tokens.colors.accent.coral,
      color: tokens.colors.base.surfaceAlt,
      boxShadow: tokens.shadows.button,
    },
  };

  const [isHovered, setIsHovered] = React.useState(false);
  const [isActive, setIsActive] = React.useState(false);

  const interactionStyles: React.CSSProperties = {};

  if (!disabled && !loading) {
    if (isActive) {
      interactionStyles.transform = tokens.effects.activeTransform;
      interactionStyles.boxShadow = 'none';
    } else if (isHovered) {
      interactionStyles.transform = tokens.effects.hoverTransform;
      if (variant !== 'ghost') {
        interactionStyles.boxShadow = tokens.shadows.buttonHover;
      }
    }
  }

  return (
    <button
      {...props}
      disabled={disabled || loading}
      style={{
        ...baseStyles,
        ...sizeStyles[size],
        ...variantStyles[variant],
        ...interactionStyles,
        ...style,
      }}
      onMouseEnter={(e) => {
        setIsHovered(true);
        props.onMouseEnter?.(e);
      }}
      onMouseLeave={(e) => {
        setIsHovered(false);
        setIsActive(false);
        props.onMouseLeave?.(e);
      }}
      onMouseDown={(e) => {
        setIsActive(true);
        props.onMouseDown?.(e);
      }}
      onMouseUp={(e) => {
        setIsActive(false);
        props.onMouseUp?.(e);
      }}
    >
      {loading && (
        <span
          style={{
            width: '16px',
            height: '16px',
            border: `2px solid ${tokens.colors.base.border}`,
            borderTopColor: 'transparent',
            borderRadius: '50%',
            animation: 'spin 0.6s linear infinite',
          }}
        />
      )}
      {children}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </button>
  );
};
