import React from 'react';
import { tokens } from '../tokens';

export interface Segment {
  label: string;
  value: string;
  disabled?: boolean;
}

export interface SegmentedControlProps {
  segments: Segment[];
  value?: string;
  onChange?: (value: string) => void;
  size?: 'sm' | 'md' | 'lg';
}

export const SegmentedControl: React.FC<SegmentedControlProps> = ({
  segments,
  value,
  onChange,
  size = 'md',
}) => {
  const [selected, setSelected] = React.useState(value || segments[0]?.value);

  React.useEffect(() => {
    if (value) setSelected(value);
  }, [value]);

  const handleSelect = (segmentValue: string, disabled?: boolean) => {
    if (disabled) return;
    setSelected(segmentValue);
    onChange?.(segmentValue);
  };

  const sizes = {
    sm: { height: '32px', padding: '6px 12px', fontSize: '14px' },
    md: { height: '40px', padding: '8px 16px', fontSize: '16px' },
    lg: { height: '48px', padding: '12px 20px', fontSize: '18px' },
  };

  const currentSize = sizes[size];

  const containerStyles: React.CSSProperties = {
    display: 'inline-flex',
    backgroundColor: tokens.colors.base.surface,
    border: `${tokens.borderWidth.default} solid ${tokens.colors.base.border}`,
    borderRadius: tokens.borderRadius.sm,
    padding: '2px',
    gap: '2px',
  };

  const segmentStyles = (segment: Segment, isActive: boolean): React.CSSProperties => ({
    height: currentSize.height,
    padding: currentSize.padding,
    fontSize: currentSize.fontSize,
    fontFamily: tokens.typography.fontFamily.sans,
    fontWeight: isActive ? tokens.typography.fontWeight.semibold : tokens.typography.fontWeight.regular,
    color: segment.disabled ? tokens.colors.base.textSecondary : tokens.colors.base.textPrimary,
    backgroundColor: isActive ? tokens.colors.accent.primaryBlue : 'transparent',
    border: isActive ? `${tokens.borderWidth.default} solid ${tokens.colors.base.border}` : 'none',
    borderRadius: tokens.borderRadius.sm,
    cursor: segment.disabled ? 'not-allowed' : 'pointer',
    transition: `all ${tokens.transitions.fast}`,
    opacity: segment.disabled ? 0.5 : 1,
    whiteSpace: 'nowrap',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  });

  return (
    <div style={containerStyles}>
      {segments.map((segment) => {
        const isActive = selected === segment.value;
        return (
          <button
            key={segment.value}
            style={segmentStyles(segment, isActive)}
            onClick={() => handleSelect(segment.value, segment.disabled)}
            onMouseEnter={(e) => {
              if (!segment.disabled && !isActive) {
                e.currentTarget.style.backgroundColor = tokens.colors.feature.lightBlue;
              }
            }}
            onMouseLeave={(e) => {
              if (!segment.disabled && !isActive) {
                e.currentTarget.style.backgroundColor = 'transparent';
              }
            }}
            disabled={segment.disabled}
          >
            {segment.label}
          </button>
        );
      })}
    </div>
  );
};
