import React from 'react';
import { tokens } from '../tokens';

export interface Tab {
  label: string;
  value: string;
  disabled?: boolean;
}

export interface TabBarProps {
  tabs: Tab[];
  activeTab?: string;
  onChange?: (value: string) => void;
  variant?: 'underline' | 'filled';
}

export const TabBar: React.FC<TabBarProps> = ({
  tabs,
  activeTab,
  onChange,
  variant = 'underline',
}) => {
  const [selected, setSelected] = React.useState(activeTab || tabs[0]?.value);

  React.useEffect(() => {
    if (activeTab) setSelected(activeTab);
  }, [activeTab]);

  const handleTabClick = (value: string, disabled?: boolean) => {
    if (disabled) return;
    setSelected(value);
    onChange?.(value);
  };

  const containerStyles: React.CSSProperties = {
    display: 'flex',
    gap: variant === 'underline' ? tokens.gap.lg : tokens.gap.xs,
    borderBottom: variant === 'underline'
      ? `${tokens.borderWidth.default} solid ${tokens.colors.base.border}`
      : 'none',
    padding: variant === 'filled' ? tokens.spacing.xs : '0',
    backgroundColor: variant === 'filled' ? tokens.colors.base.surface : 'transparent',
    border: variant === 'filled' ? `${tokens.borderWidth.default} solid ${tokens.colors.base.border}` : 'none',
    borderRadius: variant === 'filled' ? tokens.borderRadius.sm : '0',
  };

  const tabStyles = (tab: Tab, isActive: boolean): React.CSSProperties => {
    if (variant === 'underline') {
      return {
        padding: `${tokens.spacing.md} ${tokens.spacing.lg}`,
        fontFamily: tokens.typography.fontFamily.sans,
        fontSize: tokens.typography.fontSize.body.mobile,
        fontWeight: isActive ? tokens.typography.fontWeight.semibold : tokens.typography.fontWeight.regular,
        color: tab.disabled ? tokens.colors.base.textSecondary : tokens.colors.base.textPrimary,
        backgroundColor: 'transparent',
        border: 'none',
        borderBottom: `${tokens.borderWidth.thick} solid ${isActive ? tokens.colors.accent.primaryBlue : 'transparent'}`,
        cursor: tab.disabled ? 'not-allowed' : 'pointer',
        transition: `all ${tokens.transitions.fast}`,
        opacity: tab.disabled ? 0.5 : 1,
        position: 'relative',
        bottom: '-2px',
      };
    } else {
      return {
        flex: 1,
        padding: `${tokens.spacing.sm} ${tokens.spacing.lg}`,
        fontFamily: tokens.typography.fontFamily.sans,
        fontSize: tokens.typography.fontSize.body.mobile,
        fontWeight: isActive ? tokens.typography.fontWeight.semibold : tokens.typography.fontWeight.regular,
        color: tab.disabled ? tokens.colors.base.textSecondary : tokens.colors.base.textPrimary,
        backgroundColor: isActive ? tokens.colors.accent.primaryBlue : 'transparent',
        border: isActive ? `${tokens.borderWidth.default} solid ${tokens.colors.base.border}` : 'none',
        borderRadius: tokens.borderRadius.sm,
        cursor: tab.disabled ? 'not-allowed' : 'pointer',
        transition: `all ${tokens.transitions.fast}`,
        opacity: tab.disabled ? 0.5 : 1,
        textAlign: 'center',
      };
    }
  };

  return (
    <div style={containerStyles}>
      {tabs.map((tab) => {
        const isActive = selected === tab.value;
        return (
          <button
            key={tab.value}
            style={tabStyles(tab, isActive)}
            onClick={() => handleTabClick(tab.value, tab.disabled)}
            onMouseEnter={(e) => {
              if (!tab.disabled && !isActive && variant === 'filled') {
                e.currentTarget.style.backgroundColor = tokens.colors.feature.lightBlue;
              }
            }}
            onMouseLeave={(e) => {
              if (!tab.disabled && !isActive && variant === 'filled') {
                e.currentTarget.style.backgroundColor = 'transparent';
              }
            }}
            disabled={tab.disabled}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
};
