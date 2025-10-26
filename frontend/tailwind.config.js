/** @type {import('tailwindcss').Config} */
module.exports = {
  // NOTE: Update this to include the paths to all files that contain Nativewind classes.
  content: ["./app/**/*.{js,jsx,ts,tsx}", "./components/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        'black': {
          DEFAULT: '#000000',
          100: '#000000',
          200: '#000000',
          300: '#000000',
          400: '#000000',
          500: '#000000',
          600: '#333333',
          700: '#666666',
          800: '#999999',
          900: '#cccccc'
        },
        'rich_black': {
          DEFAULT: '#111827',
          100: '#030508',
          200: '#070a10',
          300: '#0a0e17',
          400: '#0e131f',
          500: '#111827',
          600: '#2d3f66',
          700: '#4866a5',
          800: '#8197c8',
          900: '#c0cbe3'
        },
        'charcoal': {
          DEFAULT: '#374151',
          100: '#0b0d10',
          200: '#161a21',
          300: '#212731',
          400: '#2d3542',
          500: '#374151',
          600: '#56657e',
          700: '#7a8aa5',
          800: '#a6b1c3',
          900: '#d3d8e1'
        },
        'charcoal_alt': {
          DEFAULT: '#4b5563',
          100: '#0f1114',
          200: '#1e2228',
          300: '#2d333b',
          400: '#3c444f',
          500: '#4b5563',
          600: '#687689',
          700: '#8c98a8',
          800: '#b2bac5',
          900: '#d9dde2'
        },
        'dim_gray': {
          DEFAULT: '#6f6f6f',
          100: '#161616',
          200: '#2d2d2d',
          300: '#434343',
          400: '#5a5a5a',
          500: '#6f6f6f',
          600: '#8d8d8d',
          700: '#a9a9a9',
          800: '#c6c6c6',
          900: '#e2e2e2'
        },
        'dark_slate_gray': {
          DEFAULT: '#204e4d',
          100: '#071010',
          200: '#0d2020',
          300: '#14302f',
          400: '#1a403f',
          500: '#204e4d',
          600: '#388887',
          700: '#56bab8',
          800: '#8ed1d0',
          900: '#c7e8e7'
        },
        'fern_green': {
          DEFAULT: '#3a7f3a',
          100: '#0c190c',
          200: '#173217',
          300: '#234b23',
          400: '#2e652e',
          500: '#3a7f3a',
          600: '#4eaa4e',
          700: '#79c179',
          800: '#a6d6a6',
          900: '#d2ead2'
        },
        'mantis': {
          DEFAULT: '#6db46d',
          100: '#142614',
          200: '#284d28',
          300: '#3b733b',
          400: '#4f994f',
          500: '#6db46d',
          600: '#8bc38b',
          700: '#a8d2a8',
          800: '#c5e1c5',
          900: '#e2f0e2'
        },
        'white': {
          DEFAULT: '#ffffff',
          100: '#333333',
          200: '#666666',
          300: '#999999',
          400: '#cccccc',
          500: '#ffffff',
          600: '#ffffff',
          700: '#ffffff',
          800: '#ffffff',
          900: '#ffffff'
        },
        'anti_flash_white': {
          DEFAULT: '#e5e7eb',
          100: '#282c34',
          200: '#515969',
          300: '#7c869a',
          400: '#b1b7c3',
          500: '#e5e7eb',
          600: '#eaecef',
          700: '#eff1f3',
          800: '#f5f5f7',
          900: '#fafafb'
        }
      }
    },
  },
  plugins: [],
}