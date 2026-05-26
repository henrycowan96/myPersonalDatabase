// Design Tokens for Minimalist Monochrome with Purple/Dark Theme
// Adapts monochrome principles while preserving the purple accent

export const Colors = {
  // Backgrounds - keeping dark theme
  background: '#000000',
  backgroundSecondary: '#0f172a',
  backgroundTertiary: '#020617',
  
  // Foreground
  foreground: '#FFFFFF',
  foregroundMuted: '#525252',
  
  // Accent - preserving purple
  accent: '#9333ea',
  accentForeground: '#FFFFFF',
  
  // Borders
  border: '#000000',
  borderLight: '#E5E5E5',
  borderAccent: '#9333ea',
  
  // Cards
  card: '#FFFFFF',
  cardForeground: '#000000',
  cardDark: '#0f172a',
  cardDarkForeground: '#FFFFFF',
  
  // Text
  textPrimary: '#FFFFFF',
  textSecondary: '#525252',
  textTertiary: '#ffffff60',
  
  // Category colors (monochrome-adapted with purple accent)
  categoryDefault: '#9333ea',
  categoryUrgent: '#9333ea',
  categoryMilestone: '#9333ea',
  categoryTrending: '#9333ea',
  categoryImportant: '#9333ea',
};

export const Typography = {
  // Font families
  fontFamilyDisplay: 'PlayfairDisplay',
  fontFamilyBody: 'SourceSerif4',
  fontFamilyMono: 'JetBrainsMono',
  
  // Type scale (dramatic range)
  fontSize: {
    xs: 12,
    sm: 14,
    base: 16,
    lg: 18,
    xl: 20,
    '2xl': 24,
    '3xl': 32,
    '4xl': 40,
    '5xl': 56,
    '6xl': 72,
    '7xl': 96,
    '8xl': 128,
    '9xl': 160,
  },
  
  // Line heights
  lineHeight: {
    none: 1,
    tight: 1.25,
    normal: 1.5,
    relaxed: 1.625,
    loose: 2,
  },
  
  // Letter spacing
  letterSpacing: {
    tighter: -0.05,
    tight: -0.025,
    normal: 0,
    wide: 0.025,
    wider: 0.05,
    widest: 0.1,
  },
  
  // Font weights
  fontWeight: {
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },
};

export const Spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  '2xl': 48,
  '3xl': 64,
  '4xl': 96,
  '5xl': 128,
};

export const Border = {
  // All corners are sharp (0px)
  radius: {
    none: 0,
    sm: 0,
    md: 0,
    lg: 0,
    xl: 0,
    '2xl': 0,
    full: 0,
  },
  
  // Border widths
  width: {
    hairline: 1,
    thin: 1,
    medium: 2,
    thick: 4,
    ultra: 8,
  },
};

export const Shadow = {
  // No shadows in monochrome design
  none: {
    shadowColor: 'transparent',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0,
    shadowRadius: 0,
    elevation: 0,
  },
};

export const Animation = {
  // Instant transitions (minimal and binary)
  duration: {
    instant: 0,
    fast: 100,
    normal: 300,
  },
  
  // No easing - instant state changes
  easing: {
    linear: 'linear',
  },
};

export const Texture = {
  // Horizontal lines pattern (global)
  horizontalLines: {
    background: 'repeating-linear-gradient(0deg, transparent, transparent 1px, #000 1px, #000 2px)',
    backgroundSize: '100% 4px',
    opacity: 0.015,
  },
  
  // Grid pattern (editorial sections)
  grid: {
    background: 'linear-gradient(#00000008 1px, transparent 1px), linear-gradient(90deg, #00000008 1px, transparent 1px)',
    backgroundSize: '40px 40px',
    opacity: 0.015,
  },
  
  // Diagonal lines (process/timeline)
  diagonal: {
    background: 'repeating-linear-gradient(45deg, transparent, transparent 40px, #00000008 40px, #00000008 42px)',
    opacity: 0.01,
  },
  
  // Noise texture (paper-like quality)
  noise: {
    background: 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 256 256\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noise\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.8\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noise)\'/%3E%3C/svg%3E")',
    opacity: 0.02,
  },
};

export const Layout = {
  // Container
  maxWidth: {
    container: 1152, // 72rem
  },
  
  // Section spacing
  padding: {
    sectionVertical: {
      mobile: 96, // py-24
      tablet: 128, // py-32
      desktop: 160, // py-40
    },
    containerHorizontal: {
      mobile: 24, // px-6
      tablet: 32, // px-8
      desktop: 48, // px-12
    },
  },
};

export const Icon = {
  // Thin stroke icons
  strokeWidth: {
    thin: 1,
    normal: 1.5,
  },
  
  size: {
    xs: 16,
    sm: 20,
    md: 24,
    lg: 32,
    xl: 48,
  },
};

export default {
  Colors,
  Typography,
  Spacing,
  Border,
  Shadow,
  Animation,
  Texture,
  Layout,
  Icon,
};
