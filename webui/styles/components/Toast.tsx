import React from 'react';
import { tokens } from '../tokens';

export interface ToastProps {
  message: string;
  variant?: 'info' | 'success' | 'warning' | 'error';
  duration?: number;
  onClose?: () => void;
  position?: 'top' | 'bottom';
}

export const Toast: React.FC<ToastProps> = ({
  message,
  variant = 'info',
  duration = 3000,
  onClose,
  position = 'top',
}) => {
  const [isVisible, setIsVisible] = React.useState(true);

  React.useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => {
        setIsVisible(false);
        setTimeout(() => onClose?.(), 300);
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [duration, onClose]);

  if (!isVisible) return null;

  const variantStyles: Record<string, React.CSSProperties> = {
    info: {
      backgroundColor: tokens.colors.accent.primaryBlue,
      color: tokens.colors.base.textPrimary,
    },
    success: {
      backgroundColor: tokens.colors.accent.green,
      color: tokens.colors.base.surfaceAlt,
    },
    warning: {
      backgroundColor: tokens.colors.accent.yellow,
      color: tokens.colors.base.textPrimary,
    },
    error: {
      backgroundColor: tokens.colors.accent.coral,
      color: tokens.colors.base.surfaceAlt,
    },
  };

  const toastStyles: React.CSSProperties = {
    position: 'fixed',
    ...(position === 'top' ? { top: tokens.spacing.lg } : { bottom: tokens.spacing.lg }),
    left: '50%',
    transform: 'translateX(-50%)',
    padding: `${tokens.spacing.md} ${tokens.spacing.lg}`,
    border: `${tokens.borderWidth.default} solid ${tokens.colors.base.border}`,
    borderRadius: tokens.borderRadius.sm,
    boxShadow: tokens.shadows.card,
    fontFamily: tokens.typography.fontFamily.sans,
    fontSize: tokens.typography.fontSize.body.mobile,
    fontWeight: tokens.typography.fontWeight.semibold,
    display: 'flex',
    alignItems: 'center',
    gap: tokens.gap.md,
    zIndex: 1000,
    minWidth: '300px',
    maxWidth: '500px',
    animation: position === 'top' ? 'slideInDown 300ms ease-out' : 'slideInUp 300ms ease-out',
    ...variantStyles[variant],
  };

  const closeButtonStyles: React.CSSProperties = {
    background: 'transparent',
    border: 'none',
    fontSize: '20px',
    fontWeight: tokens.typography.fontWeight.bold,
    color: 'inherit',
    cursor: 'pointer',
    padding: '0',
    marginLeft: 'auto',
    lineHeight: 1,
    transition: `opacity ${tokens.transitions.fast}`,
  };

  const handleClose = () => {
    setIsVisible(false);
    setTimeout(() => onClose?.(), 300);
  };

  return (
    <>
      <style>{`
        @keyframes slideInDown {
          from {
            opacity: 0;
            transform: translate(-50%, -20px);
          }
          to {
            opacity: 1;
            transform: translate(-50%, 0);
          }
        }
        @keyframes slideInUp {
          from {
            opacity: 0;
            transform: translate(-50%, 20px);
          }
          to {
            opacity: 1;
            transform: translate(-50%, 0);
          }
        }
      `}</style>
      <div style={toastStyles}>
        <span>{message}</span>
        <button
          style={closeButtonStyles}
          onClick={handleClose}
          onMouseEnter={(e) => {
            e.currentTarget.style.opacity = '0.7';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.opacity = '1';
          }}
          aria-label="Close toast"
        >
          ×
        </button>
      </div>
    </>
  );
};
