import React from 'react';
import { tokens } from '../tokens';

export interface NavBarItem {
  label: string;
  icon?: React.ReactNode;
  onClick?: () => void;
  active?: boolean;
}

export interface NavBarProps {
  items: NavBarItem[];
  position?: 'top' | 'bottom';
  logo?: React.ReactNode;
}

export const NavBar: React.FC<NavBarProps> = ({
  items,
  position = 'top',
  logo,
}) => {
  const containerStyles: React.CSSProperties = {
    position: 'fixed',
    ...(position === 'top' ? { top: 0 } : { bottom: 0 }),
    left: 0,
    right: 0,
    height: '64px',
    backgroundColor: tokens.colors.base.surface,
    borderBottom: position === 'top'
      ? `${tokens.borderWidth.default} solid ${tokens.colors.base.border}`
      : 'none',
    borderTop: position === 'bottom'
      ? `${tokens.borderWidth.default} solid ${tokens.colors.base.border}`
      : 'none',
    display: 'flex',
    alignItems: 'center',
    padding: `0 ${tokens.spacing.lg}`,
    gap: tokens.gap.xl,
    zIndex: 100,
  };

  const logoStyles: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    fontFamily: tokens.typography.fontFamily.sans,
    fontSize: tokens.typography.fontSize.h4.mobile,
    fontWeight: tokens.typography.fontWeight.bold,
    color: tokens.colors.base.textPrimary,
  };

  const navItemsStyles: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.gap.lg,
    flex: 1,
    justifyContent: position === 'bottom' ? 'space-around' : 'flex-start',
  };

  const itemStyles = (active: boolean): React.CSSProperties => ({
    display: 'flex',
    flexDirection: position === 'bottom' ? 'column' : 'row',
    alignItems: 'center',
    gap: tokens.gap.xs,
    padding: `${tokens.spacing.sm} ${tokens.spacing.md}`,
    fontFamily: tokens.typography.fontFamily.sans,
    fontSize: tokens.typography.fontSize.body.mobile,
    fontWeight: active ? tokens.typography.fontWeight.semibold : tokens.typography.fontWeight.regular,
    color: tokens.colors.base.textPrimary,
    backgroundColor: active ? tokens.colors.feature.lightBlue : 'transparent',
    border: `${tokens.borderWidth.default} solid ${active ? tokens.colors.base.border : 'transparent'}`,
    borderRadius: tokens.borderRadius.sm,
    cursor: 'pointer',
    transition: `all ${tokens.transitions.fast}`,
    textDecoration: 'none',
    whiteSpace: 'nowrap',
  });

  return (
    <nav style={containerStyles}>
      {logo && position === 'top' && <div style={logoStyles}>{logo}</div>}
      <div style={navItemsStyles}>
        {items.map((item, index) => (
          <div
            key={index}
            style={itemStyles(item.active || false)}
            onClick={item.onClick}
            onMouseEnter={(e) => {
              if (!item.active) {
                e.currentTarget.style.backgroundColor = tokens.colors.feature.lightBlue;
                e.currentTarget.style.borderColor = tokens.colors.base.border;
              }
            }}
            onMouseLeave={(e) => {
              if (!item.active) {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.borderColor = 'transparent';
              }
            }}
          >
            {item.icon && <span>{item.icon}</span>}
            <span>{item.label}</span>
          </div>
        ))}
      </div>
    </nav>
  );
};
