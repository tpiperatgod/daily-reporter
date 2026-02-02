import React from 'react';
import { tokens } from '../tokens';

export interface CarouselProps {
  children: React.ReactNode[];
  autoPlay?: boolean;
  interval?: number;
  showDots?: boolean;
  showArrows?: boolean;
}

export const Carousel: React.FC<CarouselProps> = ({
  children,
  autoPlay = false,
  interval = 3000,
  showDots = true,
  showArrows = true,
}) => {
  const [currentIndex, setCurrentIndex] = React.useState(0);
  const itemCount = React.Children.count(children);

  React.useEffect(() => {
    if (autoPlay && itemCount > 1) {
      const timer = setInterval(() => {
        setCurrentIndex((prev) => (prev + 1) % itemCount);
      }, interval);
      return () => clearInterval(timer);
    }
  }, [autoPlay, interval, itemCount]);

  const goToSlide = (index: number) => {
    setCurrentIndex(index);
  };

  const goToPrevious = () => {
    setCurrentIndex((prev) => (prev - 1 + itemCount) % itemCount);
  };

  const goToNext = () => {
    setCurrentIndex((prev) => (prev + 1) % itemCount);
  };

  const containerStyles: React.CSSProperties = {
    position: 'relative',
    width: '100%',
    overflow: 'hidden',
    border: `${tokens.borderWidth.default} solid ${tokens.colors.base.border}`,
    borderRadius: tokens.borderRadius.sm,
    backgroundColor: tokens.colors.base.surface,
  };

  const trackStyles: React.CSSProperties = {
    display: 'flex',
    transition: `transform ${tokens.transitions.standard}`,
    transform: `translateX(-${currentIndex * 100}%)`,
  };

  const slideStyles: React.CSSProperties = {
    minWidth: '100%',
    flexShrink: 0,
  };

  const arrowButtonStyles = (direction: 'left' | 'right'): React.CSSProperties => ({
    position: 'absolute',
    top: '50%',
    [direction]: tokens.spacing.md,
    transform: 'translateY(-50%)',
    backgroundColor: tokens.colors.base.surface,
    border: `${tokens.borderWidth.default} solid ${tokens.colors.base.border}`,
    borderRadius: tokens.borderRadius.sm,
    width: '40px',
    height: '40px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    fontSize: '20px',
    fontWeight: tokens.typography.fontWeight.bold,
    color: tokens.colors.base.textPrimary,
    transition: `all ${tokens.transitions.fast}`,
    zIndex: 10,
  });

  const dotsContainerStyles: React.CSSProperties = {
    position: 'absolute',
    bottom: tokens.spacing.md,
    left: '50%',
    transform: 'translateX(-50%)',
    display: 'flex',
    gap: tokens.gap.sm,
    zIndex: 10,
  };

  const dotStyles = (isActive: boolean): React.CSSProperties => ({
    width: '10px',
    height: '10px',
    borderRadius: '50%',
    backgroundColor: isActive ? tokens.colors.accent.primaryBlue : tokens.colors.base.surface,
    border: `${tokens.borderWidth.default} solid ${tokens.colors.base.border}`,
    cursor: 'pointer',
    transition: `all ${tokens.transitions.fast}`,
  });

  return (
    <div style={containerStyles}>
      <div style={trackStyles}>
        {React.Children.map(children, (child, index) => (
          <div key={index} style={slideStyles}>
            {child}
          </div>
        ))}
      </div>

      {showArrows && itemCount > 1 && (
        <>
          <button
            style={arrowButtonStyles('left')}
            onClick={goToPrevious}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = tokens.colors.feature.lightBlue;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = tokens.colors.base.surface;
            }}
            aria-label="Previous slide"
          >
            ‹
          </button>
          <button
            style={arrowButtonStyles('right')}
            onClick={goToNext}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = tokens.colors.feature.lightBlue;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = tokens.colors.base.surface;
            }}
            aria-label="Next slide"
          >
            ›
          </button>
        </>
      )}

      {showDots && itemCount > 1 && (
        <div style={dotsContainerStyles}>
          {Array.from({ length: itemCount }, (_, index) => (
            <button
              key={index}
              style={dotStyles(index === currentIndex)}
              onClick={() => goToSlide(index)}
              aria-label={`Go to slide ${index + 1}`}
            />
          ))}
        </div>
      )}
    </div>
  );
};
