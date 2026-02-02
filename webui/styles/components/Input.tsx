import React from 'react';
import { tokens } from '../tokens';

export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size' | 'onChange'> {
  label?: string;
  size?: 'sm' | 'md' | 'lg';
  error?: boolean | string;
  hint?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  onChange?: (value: string) => void;
}

export const Input: React.FC<InputProps> = ({
  label,
  size = 'md',
  error,
  hint,
  leftIcon,
  rightIcon,
  disabled = false,
  style,
  id,
  onChange,
  ...props
}) => {
  const [isFocused, setIsFocused] = React.useState(false);
  const inputId = id || `input-${React.useId()}`;

  const sizeStyles: Record<string, React.CSSProperties> = {
    sm: {
      height: tokens.sizes.input.sm.height,
      padding: tokens.sizes.input.sm.padding,
      fontSize: tokens.sizes.input.sm.fontSize,
    },
    md: {
      height: tokens.sizes.input.md.height,
      padding: tokens.sizes.input.md.padding,
      fontSize: tokens.sizes.input.md.fontSize,
    },
    lg: {
      height: tokens.sizes.input.lg.height,
      padding: tokens.sizes.input.lg.padding,
      fontSize: tokens.sizes.input.lg.fontSize,
    },
  };

  const containerStyles: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.gap.xs,
    width: '100%',
  };

  const wrapperStyles: React.CSSProperties = {
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
    width: '100%',
  };

  const hasError = Boolean(error);
  const errorMessage = typeof error === 'string' ? error : '';

  const labelStyles: React.CSSProperties = {
    display: 'block',
    fontSize: tokens.typography.fontSize.small.mobile,
    fontFamily: tokens.typography.fontFamily.sans,
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.base.textPrimary,
    marginBottom: tokens.spacing.xs,
  };

  const inputStyles: React.CSSProperties = {
    fontFamily: tokens.typography.fontFamily.sans,
    fontWeight: tokens.typography.fontWeight.regular,
    backgroundColor: 'rgba(248, 248, 247, 0.7)',
    color: tokens.colors.base.textPrimary,
    border: `${tokens.borderWidth.default} solid ${
      hasError
        ? tokens.colors.accent.coral
        : isFocused
        ? tokens.colors.accent.activeBlue
        : tokens.colors.base.border
    }`,
    borderRadius: tokens.borderRadius.sm,
    transition: `all ${tokens.transitions.standard}`,
    outline: 'none',
    width: '100%',
    ...sizeStyles[size],
    paddingLeft: leftIcon ? '44px' : sizeStyles[size].padding,
    paddingRight: rightIcon ? '44px' : sizeStyles[size].padding,
    opacity: disabled ? 0.5 : 1,
    cursor: disabled ? 'not-allowed' : 'text',
  };

  const iconStyles: React.CSSProperties = {
    position: 'absolute',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: tokens.colors.base.textSecondary,
    pointerEvents: 'none',
  };

  const leftIconStyles: React.CSSProperties = {
    ...iconStyles,
    left: tokens.spacing.md,
  };

  const rightIconStyles: React.CSSProperties = {
    ...iconStyles,
    right: tokens.spacing.md,
  };

  const hintStyles: React.CSSProperties = {
    fontSize: tokens.typography.fontSize.small.mobile,
    color: hasError ? tokens.colors.accent.coral : tokens.colors.base.textSecondary,
    marginTop: tokens.spacing.xs,
  };

  return (
    <div style={containerStyles}>
      {label && (
        <label htmlFor={inputId} style={labelStyles}>
          {label}
        </label>
      )}
      <div style={wrapperStyles}>
        {leftIcon && <div style={leftIconStyles}>{leftIcon}</div>}
        <input
          {...props}
          id={inputId}
          disabled={disabled}
          style={{ ...inputStyles, ...style }}
          onChange={(e) => onChange?.(e.target.value)}
          onFocus={(e) => {
            setIsFocused(true);
            props.onFocus?.(e);
          }}
          onBlur={(e) => {
            setIsFocused(false);
            props.onBlur?.(e);
          }}
        />
        {rightIcon && <div style={rightIconStyles}>{rightIcon}</div>}
      </div>
      {errorMessage && <div style={hintStyles}>{errorMessage}</div>}
      {hint && !hasError && <div style={hintStyles}>{hint}</div>}
    </div>
  );
};
