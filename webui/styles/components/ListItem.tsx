import React from 'react';
import { tokens } from '../tokens';

export interface ListItemProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  subtitle?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  rightElement?: React.ReactNode;
  hoverable?: boolean;
  active?: boolean;
  disabled?: boolean;
}

export const ListItem: React.FC<ListItemProps> = ({
  title,
  subtitle,
  leftIcon,
  rightIcon,
  rightElement,
  hoverable = true,
  active = false,
  disabled = false,
  style,
  ...props
}) => {
  const [isHovered, setIsHovered] = React.useState(false);

  const baseStyles: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.gap.md,
    padding: tokens.spacing.lg,
    backgroundColor: active
      ? tokens.colors.feature.lightBlue
      : tokens.colors.base.surface,
    borderBottom: `${tokens.borderWidth.thin} solid ${tokens.colors.base.border}`,
    transition: `all ${tokens.transitions.standard}`,
    cursor: disabled ? 'not-allowed' : hoverable ? 'pointer' : 'default',
    opacity: disabled ? 0.5 : 1,
  };

  const hoverStyles: React.CSSProperties =
    hoverable && isHovered && !disabled
      ? {
          backgroundColor: tokens.colors.feature.lightBlue,
        }
      : {};

  const iconContainerStyles: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    color: tokens.colors.base.textSecondary,
  };

  const contentStyles: React.CSSProperties = {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.gap.xs,
    minWidth: 0,
  };

  const titleStyles: React.CSSProperties = {
    fontFamily: tokens.typography.fontFamily.sans,
    fontSize: tokens.typography.fontSize.body.mobile,
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.base.textPrimary,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  };

  const subtitleStyles: React.CSSProperties = {
    fontFamily: tokens.typography.fontFamily.sans,
    fontSize: tokens.typography.fontSize.small.mobile,
    fontWeight: tokens.typography.fontWeight.regular,
    color: tokens.colors.base.textSecondary,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  };

  const rightContainerStyles: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.gap.sm,
    flexShrink: 0,
  };

  return (
    <div
      {...props}
      style={{
        ...baseStyles,
        ...hoverStyles,
        ...style,
      }}
      onMouseEnter={(e) => {
        if (hoverable && !disabled) setIsHovered(true);
        props.onMouseEnter?.(e);
      }}
      onMouseLeave={(e) => {
        if (hoverable && !disabled) setIsHovered(false);
        props.onMouseLeave?.(e);
      }}
    >
      {leftIcon && <div style={iconContainerStyles}>{leftIcon}</div>}
      <div style={contentStyles}>
        <div style={titleStyles}>{title}</div>
        {subtitle && <div style={subtitleStyles}>{subtitle}</div>}
      </div>
      {(rightIcon || rightElement) && (
        <div style={rightContainerStyles}>
          {rightElement}
          {rightIcon && <div style={iconContainerStyles}>{rightIcon}</div>}
        </div>
      )}
    </div>
  );
};
