import React from 'react';
import { tokens } from '../tokens';

export interface RadioProps {
  checked?: boolean;
  onChange?: (checked: boolean) => void;
  disabled?: boolean;
  label?: string;
  name?: string;
  value?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const Radio: React.FC<RadioProps> = ({
  checked = false,
  onChange,
  disabled = false,
  label,
  name,
  value,
  size = 'md',
}) => {
  const [isChecked, setIsChecked] = React.useState(checked);

  React.useEffect(() => {
    setIsChecked(checked);
  }, [checked]);

  const handleChange = () => {
    if (disabled) return;
    setIsChecked(true);
    onChange?.(true);
  };

  const sizes = {
    sm: { size: 16, dotSize: 8, fontSize: '14px' },
    md: { size: 20, dotSize: 10, fontSize: '16px' },
    lg: { size: 24, dotSize: 12, fontSize: '18px' },
  };

  const currentSize = sizes[size];

  const containerStyles: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: tokens.gap.md,
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
  };

  const circleStyles: React.CSSProperties = {
    position: 'relative',
    width: `${currentSize.size}px`,
    height: `${currentSize.size}px`,
    backgroundColor: tokens.colors.base.surface,
    border: `${tokens.borderWidth.default} solid ${tokens.colors.base.border}`,
    borderRadius: '50%',
    transition: `all ${tokens.transitions.standard}`,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: disabled ? 'not-allowed' : 'pointer',
    flexShrink: 0,
  };

  const dotStyles: React.CSSProperties = {
    width: `${currentSize.dotSize}px`,
    height: `${currentSize.dotSize}px`,
    backgroundColor: tokens.colors.accent.primaryBlue,
    borderRadius: '50%',
    transform: isChecked ? 'scale(1)' : 'scale(0)',
    transition: `transform ${tokens.transitions.fast}`,
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
      <input
        type="radio"
        name={name}
        value={value}
        checked={isChecked}
        disabled={disabled}
        onChange={handleChange}
        style={{ position: 'absolute', opacity: 0, pointerEvents: 'none' }}
      />
      <div style={circleStyles}>
        <div style={dotStyles} />
      </div>
      {label && <span style={labelStyles}>{label}</span>}
    </label>
  );
};
