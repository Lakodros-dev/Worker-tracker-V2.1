# Frontend (Telegram Mini App)

## Fayllar

- `index.html` - Asosiy HTML
- `styles.css` - Stillar
- `app.js` - JavaScript
- `config.js` - API URL sozlamasi

## Deploy

1. Barcha fayllarni static hosting ga yuklang (Vercel, Netlify, GitHub Pages)
2. `config.js` faylida `API_URL` ni backend URL ga o'zgartiring

## config.js

```javascript
const API_URL = 'https://your-backend-url.com';
```

## Muhim

- HTTPS bo'lishi shart (Telegram talabi)
- Backend CORS sozlangan bo'lishi kerak
