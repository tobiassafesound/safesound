import { defineConfig } from 'tailwindcss/helpers'

export default {
  content: ['./src/**/*.{astro,html,js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        safesound: {
          primary: '#189B75',   // Verde principal
          secondary: '#007A57', // Verde oscuro
          light: '#E6F5EF',     // Verde pálido para fondos suaves
          dark: '#003F2D',      // Para headers / textos
        },
        neutralwhite: '#FFFFFF',
        neutralgray: '#F7F8F8',
      },
      boxShadow: {
        soft: '0 4px 20px rgba(0, 0, 0, 0.08)',
      },
      borderRadius: {
        '2xl': '1rem',
      },
    },
  },
  plugins: [],
};
