import React from 'react';
import { tokens } from '../tokens';

export interface DropdownOption {
  label: string;
  value: string;
  disabled?: boolean;
}

export interface DropdownProps {
  options: DropdownOption[];
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export const Dropdown: React.FC<DropdownProps> = ({
  options,
  value,
  onChange,
  placeholder = 'Select an option',
  disabled = false,
  size = 'md',
}) => {
  const [isOpen, setIsOpen] = React.useState(false);
  const [selectedValue, setSelectedValue] = React.useState(value);
  const dropdownRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    setSelectedValue(value);
  }, [value]);

  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleSelect = (optionValue: string) => {
    if (disabled) return;
    setSelectedValue(optionValue);
    onChange?.(optionValue);
    setIsOpen(false);
  };

  const selectedOption = options.find((opt) => opt.value === selectedValue);

  const sizes = {
    sm: { height: '40px', padding: '8px 12px', fontSize: '14px' },
    md: { height: '48px', padding: '12px 16px', fontSize: '16px' },
    lg: { height: '58px', padding: '16px 20px', fontSize: '18px' },
  };

  const currentSize = sizes[size];

  const containerStyles: React.CSSProperties = {
    position: 'relative',
    width: '100%',
  };

  const triggerStyles: React.CSSProperties = {
    width: '100%',
    height: currentSize.height,
    padding: currentSize.padding,
    fontSize: currentSize.fontSize,
    fontFamily: tokens.typography.fontFamily.sans,
    fontWeight: tokens.typography.fontWeight.regular,
    backgroundColor: 'rgba(248, 248, 247, 0.7)',
    color: selectedOption ? tokens.colors.base.textPrimary : tokens.colors.base.textSecondary,
    border: `${tokens.borderWidth.default} solid ${
      isOpen ? tokens.colors.accent.activeBlue : tokens.colors.base.border
    }`,
    borderRadius: tokens.borderRadius.sm,
    cursor: disabled ? 'not-allowed' : 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    transition: `all ${tokens.transitions.standard}`,
    opacity: disabled ? 0.5 : 1,
  };

  const menuStyles: React.CSSProperties = {
    position: 'absolute',
    top: `calc(${currentSize.height} + 4px)`,
    left: 0,
    right: 0,
    backgroundColor: tokens.colors.base.surface,
    border: `${tokens.borderWidth.default} solid ${tokens.colors.base.border}`,
    borderRadius: tokens.borderRadius.sm,
    boxShadow: tokens.shadows.card,
    maxHeight: '240px',
    overflowY: 'auto',
    zIndex: 100,
    animation: 'fadeIn 150ms ease-in-out',
  };

  const optionStyles = (option: DropdownOption, isSelected: boolean): React.CSSProperties => ({
    padding: tokens.spacing.md,
    fontSize: currentSize.fontSize,
    fontFamily: tokens.typography.fontFamily.sans,
    fontWeight: tokens.typography.fontWeight.regular,
    color: option.disabled ? tokens.colors.base.textSecondary : tokens.colors.base.textPrimary,
    backgroundColor: isSelected ? tokens.colors.feature.lightBlue : 'transparent',
    cursor: option.disabled ? 'not-allowed' : 'pointer',
    borderBottom: `${tokens.borderWidth.thin} solid ${tokens.colors.base.border}`,
    transition: `background-color ${tokens.transitions.fast}`,
    opacity: option.disabled ? 0.5 : 1,
  });

  const arrowStyles: React.CSSProperties = {
    fontSize: '12px',
    transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
    transition: `transform ${tokens.transitions.fast}`,
  };

  return (
    <>
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-4px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
      <div ref={dropdownRef} style={containerStyles}>
        <div
          style={triggerStyles}
          onClick={() => !disabled && setIsOpen(!isOpen)}
        >
          <span>{selectedOption ? selectedOption.label : placeholder}</span>
          <span style={arrowStyles}>▼</span>
        </div>
        {isOpen && (
          <div style={menuStyles}>
            {options.map((option) => (
              <div
                key={option.value}
                style={optionStyles(option, option.value === selectedValue)}
                onClick={() => !option.disabled && handleSelect(option.value)}
                onMouseEnter={(e) => {
                  if (!option.disabled) {
                    e.currentTarget.style.backgroundColor = tokens.colors.feature.lightBlue;
                  }
                }}
                onMouseLeave={(e) => {
                  if (!option.disabled && option.value !== selectedValue) {
                    e.currentTarget.style.backgroundColor = 'transparent';
                  }
                }}
              >
                {option.label}
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
};
