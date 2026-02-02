import React from 'react';
import { tokens } from '../tokens';

export interface ToggleProps {
  checked?: boolean;
  onChange?: (checked: boolean) => void;
  disabled?: boolean;
  label?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const Toggle: React.FC<ToggleProps> = ({
  checked = false,
  onChange,
  disabled = false,
  label,
  size = 'md',
}) => {
  const [isChecked, setIsChecked] = React.useState(checked);

  React.useEffect(() => {
    setIsChecked(checked);
  }, [checked]);

  const handleToggle = () => {
    if (disabled) return;
    const newValue = !isChecked;
    setIsChecked(newValue);
    onChange?.(newValue);
  };

  const sizes = {
    sm: { width: 36, height: 20, thumbSize: 14, padding: 2 },
    md: { width: 48, height: 26, thumbSize: 20, padding: 2 },
    lg: { width: 60, height: 32, thumbSize: 26, padding: 2 },
  };

  const currentSize = sizes[size];

  const containerStyles: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: tokens.gap.md,
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
  };

  const trackStyles: React.CSSProperties = {
    position: 'relative',
    width: `${currentSize.width}px`,
    height: `${currentSize.height}px`,
    backgroundColor: isChecked
      ? tokens.colors.accent.primaryBlue
      : tokens.colors.base.surface,
    border: `${tokens.borderWidth.default} solid ${tokens.colors.base.border}`,
    borderRadius: `${currentSize.height}px`,
    transition: `all ${tokens.transitions.standard}`,
    cursor: disabled ? 'not-allowed' : 'pointer',
  };

  const thumbStyles: React.CSSProperties = {
    position: 'absolute',
    top: `${currentSize.padding}px`,
    left: isChecked
      ? `${currentSize.width - currentSize.thumbSize - currentSize.padding - 2}px`
      : `${currentSize.padding}px`,
    width: `${currentSize.thumbSize}px`,
    height: `${currentSize.thumbSize}px`,
    backgroundColor: tokens.colors.base.surfaceAlt,
    border: `${tokens.borderWidth.default} solid ${tokens.colors.base.border}`,
    borderRadius: '50%',
    transition: `all ${tokens.transitions.standard}`,
  };

  const labelStyles: React.CSSProperties = {
    fontFamily: tokens.typography.fontFamily.sans,
    fontSize: size === 'sm' ? '14px' : size === 'lg' ? '18px' : '16px',
    fontWeight: tokens.typography.fontWeight.regular,
    color: tokens.colors.base.textPrimary,
    userSelect: 'none',
  };

  return (
    <label style={containerStyles} onClick={handleToggle}>
      <div style={trackStyles}>
        <div style={thumbStyles} />
      </div>
      {label && <span style={labelStyles}>{label}</span>}
    </label>
  );
};
