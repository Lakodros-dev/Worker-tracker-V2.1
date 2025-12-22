"""Authentication middleware."""
import hashlib
import hmac
import json
from urllib.parse import parse_qs, unquote
from typing import Optional
from fastapi import HTTPException, Header
from config import config
from database import db, USERS_FILE


def validate_telegram_data(init_data: str) -> Optional[dict]:
    """Validate Telegram WebApp init data."""
    try:
        parsed = parse_qs(init_data)
        received_hash = parsed.get("hash", [""])[0]
        if not received_hash:
            return None
        
        data_check_arr = []
        for key, value in sorted(parsed.items()):
            if key != "hash":
                data_check_arr.append(f"{key}={value[0]}")
        data_check_string = "\n".join(data_check_arr)
        
        secret_key = hmac.new(b"WebAppData", config.BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        if calculated_hash != received_hash:
            return None
        
        user_data = parsed.get("user", [""])[0]
        if user_data:
            return json.loads(unquote(user_data))
        return None
    except:
        return None


async def get_current_user(x_telegram_init_data: str = Header(None)):
    """Get current user from Telegram WebApp data."""
    if not x_telegram_init_data:
        raise HTTPException(status_code=401, detail="Telegram init data required")
    
    user_data = validate_telegram_data(x_telegram_init_data)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid Telegram data")
    
    user = db.find_one(USERS_FILE, "telegram_id", user_data["id"])
    if not user:
        raise HTTPException(status_code=403, detail="User not registered")
    
    if user["status"] == "blocked":
        raise HTTPException(status_code=403, detail="User blocked")
    
    if user["status"] == "pending" and not config.is_admin(user["telegram_id"]):
        raise HTTPException(status_code=403, detail="Account pending approval")
    
    return user
