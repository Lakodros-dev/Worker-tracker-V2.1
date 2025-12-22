# Backend API

## O'rnatish

```bash
cd app/backend
pip install -r requirements.txt
```

## Ishga tushirish

```bash
python main.py
```

yoki

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## .env sozlamalari

```
BOT_TOKEN=8364180575:AAF4x1Lxxny9Kd9WLH0q9Nju0iz_q_uBhO0
ADMIN_IDS=6181098940
API_HOST=0.0.0.0
API_PORT=8000
FRONTEND_URL=*
DATA_DIR=data
```

## API Endpoints

- `GET /` - Health check
- `GET /users/me` - Joriy foydalanuvchi
- `POST /sessions/start` - Sessiya boshlash
- `POST /locations/record` - Joylashuv yozish
- `POST /reports/submit` - Hisobot topshirish
- `POST /statistics/me` - Statistika
