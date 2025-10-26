module.exports = {
  content: [
    "./store/templates/**/*.html",
    "./templates/**/*.html",
    "./store/static/**/*.js"
  ],
  theme: {
    extend: {
      colors: {
        primaryPink: '#FF69B4',   // pink
        accentYellow: '#FFD24C',  // yellow
        bgWhite: '#FFFFFF'
      },
      fontFamily: {
        poppins: ['Poppins', 'sans-serif']
      },
      keyframes: {
        'card-pop': {
          '0%': { transform: 'translateY(8px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'tick-scale': {
          '0%': { transform: 'scale(0)' },
          '60%': { transform: 'scale(1.1)' },
          '100%': { transform: 'scale(1)' },
        }
      },
      animation: {
        'card-pop': 'card-pop 300ms ease-out',
        'tick-scale': 'tick-scale 700ms ease-out'
      }
    },
  },
  plugins: [],
}
