import colors from 'tailwindcss/colors';

/**
 * Cloudera 2025 brand theme.
 *
 * The UI was written against a dark gray-900/gray-800 palette. Rather than
 * touching ~90 components, the neutral scales are remapped here so that the
 * "dark" end (900/800/700) becomes the white / soft-gray surfaces of the
 * 2025 Cloudera slide template and the "light" end (400/300/200) becomes
 * readable dark text. Hue scales are remapped the same way: 900/800 become
 * light tints (badge/alert backgrounds), 400/300/200 become dark readable text,
 * 500/600/700 stay solid for buttons and status pills.
 *
 * Brand swatches (theme colors of 2025_Cloudera_new_brand_TOOLKIT_PPT.pptx):
 *   INDIGO #100045 · ORANGE #FF550C · BLUE #5555F9 · BLUE_LT #8789FB
 *   ORANGE_LT #FE8756 · GRAY #A8AFB9 · NEAR_BLACK #1A1A26 · SOFT_BG #F5F5FA
 */
const brand = {
  indigo: '#100045',
  'indigo-deep': '#110046',
  purple: '#26177B',
  blue: '#5555F9',
  'blue-lt': '#8789FB',
  orange: '#FF550C',
  'orange-lt': '#FE8756',
  gray: '#A8AFB9',
  ink: '#1A1A26',
  soft: '#F5F5FA',
  white: '#FFFFFF',
};

// Neutral scale: 900 = page background, 800 = card, 700/600 = borders & subtle fills,
// 500/400/300/200 = muted → strong text. 50/100 stay light (used as light tints).
const neutral = {
  50: '#F7F7FB',
  100: '#EEEFF5',
  200: '#2A2A3D',
  300: '#3B3F52',
  400: '#5B6170',
  500: '#7C8494',
  600: '#C9CCD8',
  700: '#E6E7EF',
  750: '#F0F1F7',
  800: '#FFFFFF',
  900: '#F5F5FA',
  950: '#EDEDF5',
};

/** Invert a Tailwind hue: light tints where dark was, dark text where light was. */
const invert = (c) => ({
  50: c[50],
  100: c[100],
  200: c[900],
  300: c[800],
  400: c[700],
  500: c[500],
  600: c[600],
  700: c[700],
  800: c[100],
  900: c[50],
  950: c[50],
});

// Brand-blue ramp (Cloudera BLUE #5555F9)
const blue = {
  50: '#F3F4FF',
  100: '#E4E6FF',
  200: '#22227F',
  300: '#2E2EA8',
  400: '#3D3DCC',
  500: '#5555F9',
  600: '#4444E0',
  700: '#3333C2',
  800: '#DFE1FF',
  900: '#EEEFFF',
  950: '#F3F4FF',
};

// Brand-orange ramp (Cloudera ORANGE #FF550C)
const orange = {
  50: '#FFF5F0',
  100: '#FFE1D1',
  200: '#8F2E06',
  300: '#B53A08',
  400: '#D9480C',
  500: '#FF550C',
  600: '#E84C08',
  700: '#C74003',
  800: '#FFE6DB',
  900: '#FFF1EA',
  950: '#FFF5F0',
};

// Brand-purple ramp (Cloudera PURPLE #26177B) — used for indigo/purple/violet accents
const purple = {
  50: '#F5F3FB',
  100: '#E4E0F5',
  200: '#1F1266',
  300: '#2B1D86',
  400: '#3B2AA0',
  500: '#26177B',
  600: '#1F1266',
  700: '#180D52',
  800: '#E9E6F7',
  900: '#F2F0FA',
  950: '#F5F3FB',
};

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    fontFamily: {
      sans: ['Arial', 'Helvetica Neue', 'Helvetica', 'Liberation Sans', 'sans-serif'],
      mono: ['Consolas', 'Menlo', 'Monaco', 'Liberation Mono', 'Courier New', 'monospace'],
    },
    extend: {
      colors: {
        brand,
        gray: neutral,
        slate: neutral,
        zinc: neutral,
        neutral,
        stone: neutral,
        blue,
        orange,
        indigo: purple,
        purple,
        violet: purple,
        sky: blue,
        red: invert(colors.red),
        rose: invert(colors.rose),
        pink: invert(colors.pink),
        green: invert(colors.green),
        emerald: invert(colors.emerald),
        teal: invert(colors.teal),
        lime: invert(colors.lime),
        cyan: invert(colors.cyan),
        amber: invert(colors.amber),
        yellow: invert(colors.yellow),
        fuchsia: invert(colors.fuchsia),
        'tower-healthy': '#10b981',
        'tower-degraded': '#f59e0b',
        'tower-outage': '#ef4444',
        'tower-maintenance': '#6b7280',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
}
