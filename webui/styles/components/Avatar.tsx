import React from 'react';
import { tokens } from '../tokens';

export interface AvatarProps {
  src?: string;
  alt?: string;
  name?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  shape?: 'circle' | 'square';
  fallbackColor?: string;
  status?: 'online' | 'offline' | 'away' | 'busy';
  showBadge?: boolean;
  badgeContent?: string | number;
}

interface AvatarGroupProps {
  children: React.ReactNode[];
  max?: number;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

const AvatarComponent: React.FC<AvatarProps> = ({
  src,
  alt,
  name,
  size = 'md',
  shape = 'circle',
  fallbackColor,
  status,
  showBadge = false,
  badgeContent,
}) => {
  const [imageError, setImageError] = React.useState(false);

  const sizes = {
    sm: 32,
    md: 40,
    lg: 56,
    xl: 80,
  };

  const statusSizes = {
    sm: 8,
    md: 10,
    lg: 12,
    xl: 14,
  };

  const statusColors = {
    online: tokens.colors.accent.green,
    offline: tokens.colors.base.textSecondary,
    away: tokens.colors.accent.yellow,
    busy: tokens.colors.accent.coral,
  };

  const avatarSize = sizes[size];
  const statusSize = statusSizes[size];

  const getInitials = (name: string): string => {
    const parts = name.trim().split(' ');
    if (parts.length >= 2) {
      return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  };

  // Generate a consistent color based on name
  const getNameColor = (name: string): string => {
    const colors = [
      tokens.colors.accent.primaryBlue,
      tokens.colors.accent.coral,
      tokens.colors.accent.yellow,
      tokens.colors.accent.green,
      '#10B981', // green alt
      '#F59E0B', // amber
      '#6366F1', // indigo
      '#EC4899', // pink
    ];
    const index = name.charCodeAt(0) % colors.length;
    return colors[index];
  };

  const containerStyles: React.CSSProperties = {
    position: 'relative',
    display: 'inline-block',
  };

  const baseStyles: React.CSSProperties = {
    width: `${avatarSize}px`,
    height: `${avatarSize}px`,
    borderRadius: shape === 'circle' ? '50%' : tokens.borderRadius.sm,
    border: `${tokens.borderWidth.default} solid ${tokens.colors.base.border}`,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
    flexShrink: 0,
  };

  const imageStyles: React.CSSProperties = {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  };

  const fallbackStyles: React.CSSProperties = {
    width: '100%',
    height: '100%',
    backgroundColor: fallbackColor || (name ? getNameColor(name) : tokens.colors.accent.primaryBlue),
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: tokens.typography.fontFamily.sans,
    fontSize: size === 'sm' ? '12px' : size === 'xl' ? '32px' : size === 'lg' ? '24px' : '16px',
    fontWeight: tokens.typography.fontWeight.bold,
    color: tokens.colors.base.textPrimary,
  };

  const statusIndicatorStyles: React.CSSProperties = {
    position: 'absolute',
    bottom: 0,
    right: 0,
    width: `${statusSize}px`,
    height: `${statusSize}px`,
    borderRadius: '50%',
    backgroundColor: status ? statusColors[status] : 'transparent',
    border: `${tokens.borderWidth.default} solid ${tokens.colors.base.background}`,
  };

  const badgeStyles: React.CSSProperties = {
    position: 'absolute',
    top: -4,
    right: -4,
    minWidth: '18px',
    height: '18px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '0 4px',
    fontSize: '11px',
    fontWeight: tokens.typography.fontWeight.semibold,
    fontFamily: tokens.typography.fontFamily.sans,
    color: tokens.colors.base.textPrimary,
    backgroundColor: tokens.colors.accent.coral,
    borderRadius: '9px',
    border: `${tokens.borderWidth.default} solid ${tokens.colors.base.background}`,
  };

  const showImage = src && !imageError;
  const showInitials = name && !showImage;

  return (
    <div style={containerStyles}>
      <div style={baseStyles}>
        {showImage ? (
          <img
            src={src}
            alt={alt || name || 'Avatar'}
            style={imageStyles}
            onError={() => setImageError(true)}
          />
        ) : showInitials ? (
          <div style={fallbackStyles}>{getInitials(name)}</div>
        ) : (
          <div style={fallbackStyles}>?</div>
        )}
      </div>

      {/* Status indicator */}
      {status && <span style={statusIndicatorStyles} />}

      {/* Badge */}
      {showBadge && badgeContent !== undefined && (
        <span style={badgeStyles}>
          {typeof badgeContent === 'number' && badgeContent > 99
            ? '99+'
            : badgeContent}
        </span>
      )}
    </div>
  );
};

// Avatar group component
const AvatarGroup: React.FC<AvatarGroupProps> = ({
  children,
  max = 4,
  size = 'md',
}) => {
  const visible = children.slice(0, max);
  const remaining = children.length - max;

  const overlapSizes = {
    sm: -10,
    md: -12,
    lg: -16,
    xl: -20,
  };

  const containerStyles: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
  };

  return (
    <div style={containerStyles}>
      {visible.map((child, i) => (
        <div
          key={i}
          style={{
            marginLeft: i > 0 ? `${overlapSizes[size]}px` : 0,
          }}
        >
          {child}
        </div>
      ))}
      {remaining > 0 && (
        <div
          style={{
            marginLeft: `${overlapSizes[size]}px`,
          }}
        >
          <AvatarComponent name={`+${remaining}`} size={size} />
        </div>
      )}
    </div>
  );
};

export const Avatar = Object.assign(AvatarComponent, {
  Group: AvatarGroup,
});
