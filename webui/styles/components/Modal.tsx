import React from 'react';
import { tokens } from '../tokens';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  size?: 'sm' | 'md' | 'lg';
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  footer,
  size = 'md',
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

  const sizes = {
    sm: '400px',
    md: '600px',
    lg: '800px',
  };

  const overlayStyles: React.CSSProperties = {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(56, 56, 56, 0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: tokens.spacing.lg,
    zIndex: 1000,
    animation: 'fadeIn 200ms ease-in-out',
  };

  const modalStyles: React.CSSProperties = {
    backgroundColor: tokens.colors.base.background,
    border: `${tokens.borderWidth.default} solid ${tokens.colors.base.border}`,
    borderRadius: tokens.borderRadius.sm,
    boxShadow: tokens.shadows.cardElevated,
    width: '100%',
    maxWidth: sizes[size],
    maxHeight: '90vh',
    display: 'flex',
    flexDirection: 'column',
    animation: 'slideUp 200ms ease-in-out',
  };

  const headerStyles: React.CSSProperties = {
    padding: tokens.spacing.lg,
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

  const footerStyles: React.CSSProperties = {
    padding: tokens.spacing.lg,
    borderTop: `${tokens.borderWidth.thin} solid ${tokens.colors.base.border}`,
    display: 'flex',
    gap: tokens.gap.md,
    justifyContent: 'flex-end',
  };

  return (
    <>
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
      <div style={overlayStyles} onClick={onClose}>
        <div style={modalStyles} onClick={(e) => e.stopPropagation()}>
          <div style={headerStyles}>
            {title && <h2 style={titleStyles}>{title}</h2>}
            <button
              style={closeButtonStyles}
              onClick={onClose}
              onMouseEnter={(e) => {
                e.currentTarget.style.opacity = '0.7';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.opacity = '1';
              }}
              aria-label="Close modal"
            >
              ×
            </button>
          </div>
          <div style={bodyStyles}>{children}</div>
          {footer && <div style={footerStyles}>{footer}</div>}
        </div>
      </div>
    </>
  );
};
