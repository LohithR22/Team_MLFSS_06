const theme = {
  colors: {
    primary: '#6D28D9', // Royal Purple - primary actions, icons, highlights
    primaryDark: '#5B21B6',
    primaryLight: '#7C3AED',
    secondary: '#6D28D9', // Using primary for secondary
    accent: '#F97316', // Bright Orange - accent color
    background: '#0F172A', // Off Black - main background
    surface: '#1E293B', // Dark Slate - cards and elevated surfaces
    surfaceElevated: '#334155',
    text: '#F8FAFC', // White - primary text
    textSecondary: '#CBD5E1', // Light Gray - secondary text
    textLight: '#94A3B8', // Lighter gray for tertiary text
    border: '#334155', // Dark border color
    error: '#EF4444', // Red for error
    success: '#10B981', // Green for success
    warning: '#F97316', // Using accent for warning
    info: '#6D28D9', // Using primary for info
    gradient: {
      primary: ['#6D28D9', '#5B21B6'],
      secondary: ['#6D28D9', '#7C3AED'],
      accent: ['#F97316', '#EA580C'],
      background: ['#0F172A', '#1E293B'],
    },
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
    xxl: 48,
  },
  borderRadius: {
    sm: 8,
    md: 12,
    lg: 16,
    xl: 24,
    full: 9999,
  },
  shadows: {
    sm: {
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.05,
      shadowRadius: 2,
      elevation: 2,
    },
    md: {
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.1,
      shadowRadius: 4,
      elevation: 4,
    },
    lg: {
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.15,
      shadowRadius: 8,
      elevation: 8,
    },
  },
  typography: {
    h1: {
      fontSize: 32,
      fontWeight: '700',
      lineHeight: 40,
    },
    h2: {
      fontSize: 24,
      fontWeight: '700',
      lineHeight: 32,
    },
    h3: {
      fontSize: 20,
      fontWeight: '600',
      lineHeight: 28,
    },
    h4: {
      fontSize: 18,
      fontWeight: '600',
      lineHeight: 24,
    },
    body: {
      fontSize: 16,
      fontWeight: '400',
      lineHeight: 24,
    },
    bodySmall: {
      fontSize: 14,
      fontWeight: '400',
      lineHeight: 20,
    },
    caption: {
      fontSize: 12,
      fontWeight: '400',
      lineHeight: 16,
    },
  },
};

export { theme };
export default theme;
