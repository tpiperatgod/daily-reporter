import React from 'react';
import { tokens } from '../tokens';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'elevated' | 'outlined';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  hoverable?: boolean;
  header?: React.ReactNode;
  footer?: React.ReactNode;
  children: React.ReactNode;
}

interface CardSubComponentProps {
  children: React.ReactNode;
  style?: React.CSSProperties;
}

const CardComponent: React.FC<CardProps> = ({
  variant = 'default',
  padding = 'md',
  hoverable = false,
  header,
  footer,
  children,
  style,
  onClick,
  ...props
}) => {
  const [isHovered, setIsHovered] = React.useState(false);

  const paddingValues = {
    none: '0',
    sm: tokens.spacing.sm,
    md: tokens.spacing.md,
    lg: tokens.spacing.lg,
  };

  const baseStyles: React.CSSProperties = {
    backgroundColor: tokens.colors.base.surface,
    border: variant === 'outlined'
      ? `${tokens.borderWidth.thick} solid ${tokens.colors.base.border}`
      : `${tokens.borderWidth.default} solid ${tokens.colors.base.border}`,
    borderRadius: tokens.borderRadius.sm,
    display: 'flex',
    flexDirection: 'column',
    transition: `all ${tokens.transitions.standard}`,
    padding: paddingValues[padding],
  };

  const variantStyles: Record<string, React.CSSProperties> = {
    default: {
      boxShadow: tokens.shadows.card,
    },
    elevated: {
      boxShadow: tokens.shadows.cardElevated,
    },
    outlined: {
      backgroundColor: 'transparent',
      boxShadow: 'none',
    },
  };

  const hoverStyles: React.CSSProperties = hoverable && isHovered
    ? {
        transform: 'translate(2px, -2px)',
        boxShadow: variant === 'elevated'
          ? '-14px 14px 0 ' + tokens.colors.base.border
          : variant === 'outlined'
          ? '-8px 8px 0 ' + tokens.colors.base.border
          : '-10px 10px 0 ' + tokens.colors.base.border,
      }
    : {};

  const headerStyles: React.CSSProperties = {
    padding: tokens.spacing.lg,
    borderBottom: `${tokens.borderWidth.thin} solid ${tokens.colors.base.border}`,
    fontWeight: tokens.typography.fontWeight.semibold,
    fontSize: tokens.typography.fontSize.h4.mobile,
  };

  const bodyStyles: React.CSSProperties = {
    padding: padding === 'none' ? tokens.spacing.lg : '0',
    flex: 1,
  };

  const footerStyles: React.CSSProperties = {
    padding: tokens.spacing.lg,
    borderTop: `${tokens.borderWidth.thin} solid ${tokens.colors.base.border}`,
  };

  return (
    <div
      {...props}
      onClick={onClick}
      style={{
        ...baseStyles,
        ...variantStyles[variant],
        ...hoverStyles,
        cursor: hoverable || onClick ? 'pointer' : 'default',
        ...style,
      }}
      onMouseEnter={(e) => {
        if (hoverable) setIsHovered(true);
        props.onMouseEnter?.(e);
      }}
      onMouseLeave={(e) => {
        if (hoverable) setIsHovered(false);
        props.onMouseLeave?.(e);
      }}
    >
      {header && <div style={headerStyles}>{header}</div>}
      <div style={bodyStyles}>{children}</div>
      {footer && <div style={footerStyles}>{footer}</div>}
    </div>
  );
};

// Card subcomponents
const CardHeader: React.FC<CardSubComponentProps> = ({ children, style }) => {
  const headerStyles: React.CSSProperties = {
    marginBottom: tokens.spacing.md,
    ...style,
  };

  return <div style={headerStyles}>{children}</div>;
};

const CardTitle: React.FC<CardSubComponentProps> = ({ children, style }) => {
  const titleStyles: React.CSSProperties = {
    fontFamily: tokens.typography.fontFamily.sans,
    fontSize: tokens.typography.fontSize.h4.mobile,
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.base.textPrimary,
    ...style,
  };

  return <h3 style={titleStyles}>{children}</h3>;
};

const CardDescription: React.FC<CardSubComponentProps> = ({ children, style }) => {
  const descriptionStyles: React.CSSProperties = {
    fontFamily: tokens.typography.fontFamily.sans,
    fontSize: tokens.typography.fontSize.small.mobile,
    color: tokens.colors.base.textSecondary,
    marginTop: tokens.spacing.xs,
    ...style,
  };

  return <p style={descriptionStyles}>{children}</p>;
};

const CardContent: React.FC<CardSubComponentProps> = ({ children, style }) => {
  return <div style={style}>{children}</div>;
};

const CardFooter: React.FC<CardSubComponentProps> = ({ children, style }) => {
  const footerStyles: React.CSSProperties = {
    marginTop: tokens.spacing.md,
    paddingTop: tokens.spacing.md,
    borderTop: `${tokens.borderWidth.thin} solid ${tokens.colors.base.border}`,
    ...style,
  };

  return <div style={footerStyles}>{children}</div>;
};

export const Card = Object.assign(CardComponent, {
  Header: CardHeader,
  Title: CardTitle,
  Description: CardDescription,
  Content: CardContent,
  Footer: CardFooter,
});
