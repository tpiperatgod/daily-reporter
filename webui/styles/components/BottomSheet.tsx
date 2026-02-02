import React from 'react';
import { tokens } from '../tokens';

export interface BottomSheetProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  snapPoints?: string[];
}

export const BottomSheet: React.FC<BottomSheetProps> = ({
  isOpen,
  onClose,
  title,
  children,
  snapPoints = ['50vh'],
}) => {
  React.useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const overlayStyles: React.CSSProperties = {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(56, 56, 56, 0.5)',
    zIndex: 1000,
    animation: 'fadeIn 200ms ease-in-out',
  };

  const sheetStyles: React.CSSProperties = {
    position: 'fixed',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: tokens.colors.base.background,
    border: `${tokens.borderWidth.default} solid ${tokens.colors.base.border}`,
    borderBottom: 'none',
    borderRadius: `${tokens.borderRadius.md} ${tokens.borderRadius.md} 0 0`,
    boxShadow: tokens.shadows.cardElevated,
    maxHeight: snapPoints[0],
    display: 'flex',
    flexDirection: 'column',
    animation: 'slideInUp 300ms ease-out',
  };

  const handleStyles: React.CSSProperties = {
    display: 'flex',
    justifyContent: 'center',
    padding: tokens.spacing.md,
    cursor: 'grab',
  };

  const handleBarStyles: React.CSSProperties = {
    width: '40px',
    height: '4px',
    backgroundColor: tokens.colors.base.textSecondary,
    borderRadius: '2px',
  };

  const headerStyles: React.CSSProperties = {
    padding: `${tokens.spacing.sm} ${tokens.spacing.lg}`,
    borderBottom: `${tokens.borderWidth.thin} solid ${tokens.colors.base.border}`,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  };

  const titleStyles: React.CSSProperties = {
    fontFamily: tokens.typography.fontFamily.sans,
    fontSize: tokens.typography.fontSize.h4.mobile,
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.base.textPrimary,
    margin: 0,
  };

  const closeButtonStyles: React.CSSProperties = {
    background: 'transparent',
    border: 'none',
    fontSize: '24px',
    fontWeight: tokens.typography.fontWeight.bold,
    color: tokens.colors.base.textPrimary,
    cursor: 'pointer',
    padding: tokens.spacing.xs,
    lineHeight: 1,
    transition: `opacity ${tokens.transitions.fast}`,
  };

  const bodyStyles: React.CSSProperties = {
    padding: tokens.spacing.lg,
    flex: 1,
    overflowY: 'auto',
  };

  return (
    <>
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes slideInUp {
          from {
            transform: translateY(100%);
          }
          to {
            transform: translateY(0);
          }
        }
      `}</style>
      <div style={overlayStyles} onClick={onClose} />
      <div style={sheetStyles}>
        <div style={handleStyles} onClick={onClose}>
          <div style={handleBarStyles} />
        </div>
        {title && (
          <div style={headerStyles}>
            <h2 style={titleStyles}>{title}</h2>
            <button
              style={closeButtonStyles}
              onClick={onClose}
              onMouseEnter={(e) => {
                e.currentTarget.style.opacity = '0.7';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.opacity = '1';
              }}
              aria-label="Close bottom sheet"
            >
              ×
            </button>
          </div>
        )}
        <div style={bodyStyles}>{children}</div>
      </div>
    </>
  );
};
