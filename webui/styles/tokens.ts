/**
 * MotherDuck Design Tokens
 * Playful data infrastructure design with bold borders, offset shadows, and warm neutrals
 */

export const tokens = {
  colors: {
    // Base Colors
    base: {
      background: '#F4EFEA',
      surface: '#F8F8F7',
      surfaceAlt: '#FFFFFF',
      textPrimary: '#383838',
      textSecondary: '#A1A1A1',
      border: '#383838',
    },

    // Accent Colors
    accent: {
      primaryBlue: '#6FC2FF',
      activeBlue: '#2BA5FF',
      yellow: '#FFDE00',
      coral: '#FF7169',
      green: '#07bc0c',
    },

    // Feature Section Colors (light pastels)
    feature: {
      lightBlue: '#EBF9FF',
      lightBlueAlt: '#EAF0FF',
      lightGreen: '#E8F5E9',
      lightPurple: '#F7F1FF',
      lightYellow: '#FFFDE7',
      lightYellowAlt: '#FDEDDA',
    },

    // Dark Theme
    dark: {
      background: '#1a1a1a',
      surface: '#2a2a2a',
      surfaceAlt: '#333333',
      textPrimary: '#F8F8F7',
      textSecondary: '#A1A1A1',
      border: '#4a4a4a',
      borderAlt: '#383838',
    },
  },

  typography: {
    fontFamily: {
      sans: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      mono: "'Aeonik Mono', 'Courier New', monospace",
    },

    fontSize: {
      // Responsive sizes - mobile first
      h1: {
        mobile: '30px',
        desktop: '80px',
      },
      h2: {
        mobile: '24px',
        desktop: '40px',
      },
      h3: {
        mobile: '20px',
        desktop: '28px',
      },
      h4: {
        mobile: '18px',
        desktop: '22px',
      },
      body: {
        mobile: '14px',
        desktop: '20px',
      },
      small: {
        mobile: '12px',
        desktop: '14px',
      },
    },

    fontWeight: {
      light: 300,
      regular: 400,
      semibold: 600,
      bold: 700,
    },

    letterSpacing: {
      normal: '0.02em',
      tight: '0.01em',
    },

    lineHeight: {
      tight: 1.2,
      normal: 1.5,
      relaxed: 1.8,
    },
  },

  spacing: {
    xs: '4px',
    sm: '8px',
    md: '12px',
    lg: '16px',
    xl: '24px',
    '2xl': '32px',
    '3xl': '48px',
    '4xl': '64px',
  },

  gap: {
    xs: '6px',
    sm: '8px',
    md: '12px',
    lg: '16px',
    xl: '20px',
    '2xl': '24px',
    '3xl': '32px',
  },

  borderRadius: {
    none: '0px',
    sm: '2px',
    md: '4px',
  },

  borderWidth: {
    thin: '1px',
    default: '2px',
    thick: '3px',
  },

  shadows: {
    button: '-5px 5px 0 #383838',
    buttonHover: '-12px 12px 0 #383838',
    card: '-8px 8px 0 #383838',
    cardElevated: '-12px 12px 0 #383838',
    input: 'none',

    // Dark theme shadows
    dark: {
      button: '-5px 5px 0 #4a4a4a',
      buttonHover: '-12px 12px 0 #4a4a4a',
      card: '-8px 8px 0 #4a4a4a',
      cardElevated: '-12px 12px 0 #4a4a4a',
    },
  },

  transitions: {
    fast: '120ms ease-in-out',
    standard: '200ms ease-in-out',
    slow: '300ms ease-in-out',
  },

  effects: {
    hoverTransform: 'translate(7px, -7px)',
    activeTransform: 'translate(0, 0)',
    playfulRotation: {
      slight: '-2deg',
      medium: '2deg',
    },
  },

  sizes: {
    button: {
      sm: {
        height: '36px',
        padding: '8px 16px',
        fontSize: '14px',
      },
      md: {
        height: '48px',
        padding: '12px 22px',
        fontSize: '16px',
      },
      lg: {
        height: '56px',
        padding: '16px 28px',
        fontSize: '18px',
      },
    },

    input: {
      sm: {
        height: '40px',
        padding: '8px 12px',
        fontSize: '14px',
      },
      md: {
        height: '48px',
        padding: '12px 16px',
        fontSize: '16px',
      },
      lg: {
        height: '58px',
        padding: '16px 20px',
        fontSize: '18px',
      },
    },
  },
} as const;

export type Tokens = typeof tokens;
