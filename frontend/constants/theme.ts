/**
 * Below are the colors that are used in the app. The colors are defined in the light and dark mode.
 * There are many other ways to style your app. For example, [Nativewind](https://www.nativewind.dev/), [Tamagui](https://tamagui.dev/), [unistyles](https://reactnativeunistyles.vercel.app), etc.
 */

import { Platform } from 'react-native';

const tintColorLight = '#3a7f3a'; // Fern green
const tintColorDark = '#6db46d'; // Mantis

export const Colors = {
  light: {
    text: '#111827', // Rich black
    background: '#ffffff',
    tint: tintColorLight,
    icon: '#4b5563', // Charcoal
    tabIconDefault: '#6f6f6f', // Dim gray
    tabIconSelected: tintColorLight,
    primary: '#3a7f3a', // Fern green
    secondary: '#6db46d', // Mantis
    accent: '#204e4d', // Dark slate gray
    surface: '#e5e7eb', // Anti-flash white
  },
  dark: {
    text: '#e5e7eb', // Anti-flash white
    background: '#111827', // Rich black
    tint: tintColorDark,
    icon: '#6f6f6f', // Dim gray
    tabIconDefault: '#6f6f6f',
    tabIconSelected: tintColorDark,
    primary: '#6db46d', // Mantis
    secondary: '#3a7f3a', // Fern green
    accent: '#204e4d', // Dark slate gray
    surface: '#374151', // Charcoal
  },
};

export const Fonts = Platform.select({
  ios: {
    /** iOS `UIFontDescriptorSystemDesignDefault` */
    sans: 'system-ui',
    /** iOS `UIFontDescriptorSystemDesignSerif` */
    serif: 'ui-serif',
    /** iOS `UIFontDescriptorSystemDesignRounded` */
    rounded: 'ui-rounded',
    /** iOS `UIFontDescriptorSystemDesignMonospaced` */
    mono: 'ui-monospace',
  },
  default: {
    sans: 'normal',
    serif: 'serif',
    rounded: 'normal',
    mono: 'monospace',
  },
  web: {
    sans: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    serif: "Georgia, 'Times New Roman', serif",
    rounded: "'SF Pro Rounded', 'Hiragino Maru Gothic ProN', Meiryo, 'MS PGothic', sans-serif",
    mono: "SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
  },
});
