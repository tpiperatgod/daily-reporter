import React from 'react';
import { tokens } from '../tokens';

export interface CheckboxProps {
  checked?: boolean;
  onChange?: (checked: boolean) => void;
  disabled?: boolean;
  label?: string;
  size?: 'sm' | 'md' | 'lg';
  indeterminate?: boolean;
}

export const Checkbox: React.FC<CheckboxProps> = ({
  checked = false,
  onChange,
  disabled = false,
  label,
  size = 'md',
  indeterminate = false,
}) => {
  const [isChecked, setIsChecked] = React.useState(checked);

  React.useEffect(() => {
    setIsChecked(checked);
  }, [checked]);

  const handleChange = () => {
    if (disabled) return;
    const newValue = !isChecked;
    setIsChecked(newValue);
    onChange?.(newValue);
  };

  const sizes = {
    sm: { size: 16, fontSize: '14px' },
    md: { size: 20, fontSize: '16px' },
    lg: { size: 24, fontSize: '18px' },
  };

  const currentSize = sizes[size];

  const containerStyles: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: tokens.gap.md,
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
  };

  const boxStyles: React.CSSProperties = {
    position: 'relative',
    width: `${currentSize.size}px`,
    height: `${currentSize.size}px`,
    backgroundColor: isChecked || indeterminate
      ? tokens.colors.accent.primaryBlue
      : tokens.colors.base.surface,
    border: `${tokens.borderWidth.default} solid ${tokens.colors.base.border}`,
    borderRadius: tokens.borderRadius.sm,
    transition: `all ${tokens.transitions.standard}`,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: disabled ? 'not-allowed' : 'pointer',
    flexShrink: 0,
  };

  const checkmarkStyles: React.CSSProperties = {
    color: tokens.colors.base.textPrimary,
    fontWeight: tokens.typography.fontWeight.bold,
    fontSize: `${currentSize.size - 4}px`,
    lineHeight: 1,
  };

  const labelStyles: React.CSSProperties = {
    fontFamily: tokens.typography.fontFamily.sans,
    fontSize: currentSize.fontSize,
    fontWeight: tokens.typography.fontWeight.regular,
    color: tokens.colors.base.textPrimary,
    userSelect: 'none',
  };

  return (
    <label style={containerStyles} onClick={handleChange}>
      <div style={boxStyles}>
        {indeterminate ? (
          <span style={checkmarkStyles}>−</span>
        ) : isChecked ? (
          <span style={checkmarkStyles}>✓</span>
        ) : null}
      </div>
      {label && <span style={labelStyles}>{label}</span>}
    </label>
  );
};
