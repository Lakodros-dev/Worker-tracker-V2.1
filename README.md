# Davomat Tizimi - Telegram Mini App + Bot

Xodimlar davomati va samaradorligini kuzatish tizimi.

## Loyiha tuzilishi

```
├── bot/                    # Telegram Bot
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── requirements.txt
│   └── .env
│
└── app/
    ├── backend/            # FastAPI Backend
    │   ├── main.py
    │   ├── config.py
    │   ├── database.py
    │   ├── auth.py
    │   ├── services.py
    │   ├── requirements.txt
    │   └── .env
    │
    └── frontend/           # Telegram Mini App
        ├── index.html
        ├── styles.css
        ├── app.js
        └── config.js
```

## Deploy qilish tartibi

### 1. Backend (app/backend)
- Render, Railway, yoki VPS ga deploy qiling
- URL ni oling (masalan: `https://your-backend.onrender.com`)

### 2. Frontend (app/frontend)
- Vercel, Netlify, yoki GitHub Pages ga deploy qiling
- `config.js` da `API_URL` ni backend URL ga o'zgartiring
- URL ni oling (masalan: `https://your-frontend.vercel.app`)

### 3. Bot (bot)
- VPS yoki Railway ga deploy qiling
- `.env` faylini yangilang

## Deploy qilgandan keyin kiritish kerak bo'lgan ma'lumotlar

### bot/.env
```
BOT_TOKEN=8364180575:AAF4x1Lxxny9Kd9WLH0q9Nju0iz_q_uBhO0
ADMIN_IDS=6181098940
API_URL=<BACKEND_URL>
WEBAPP_URL=<FRONTEND_URL>
DATA_DIR=data
```

### app/backend/.env
```
BOT_TOKEN=8364180575:AAF4x1Lxxny9Kd9WLH0q9Nju0iz_q_uBhO0
ADMIN_IDS=6181098940
API_HOST=0.0.0.0
API_PORT=8000
FRONTEND_URL=<FRONTEND_URL>
DATA_DIR=data
```

### app/frontend/config.js
```javascript
const API_URL = '<BACKEND_URL>';
```

## @BotFather sozlamalari

Bot uchun Mini App o'rnatish:
1. @BotFather ga `/mybots` yuboring
2. Botni tanlang
3. Bot Settings → Menu Button → Edit Menu Button URL
4. Frontend URL ni kiriting

## Foydalanuvchi holatlari

- `pending` - Ro'yxatdan o'tgan, admin tasdig'ini kutmoqda
- `active` - Faol foydalanuvchi
- `blocked` - Bloklangan

## Admin imkoniyatlari

- Foydalanuvchilarni tasdiqlash/bloklash
- Ish vaqtini sozlash
- Ofis joylashuvini belgilash
- Barcha statistikani ko'rish
