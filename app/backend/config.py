"""Backend configuration."""
import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    BOT_TOKEN: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    ADMIN_IDS: List[int] = field(default_factory=list)
    API_HOST: str = field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    API_PORT: int = field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))
    DATA_DIR: str = field(default_factory=lambda: os.getenv("DATA_DIR", "data"))
    FRONTEND_URL: str = field(default_factory=lambda: os.getenv("FRONTEND_URL", "*"))
    
    def __post_init__(self):
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        if admin_ids_str:
            self.ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
    
    def is_admin(self, user_id: int) -> bool:
        return user_id in self.ADMIN_IDS


config = Config()
