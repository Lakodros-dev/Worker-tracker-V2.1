"""Bot configuration."""
import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Bot configuration settings."""
    
    BOT_TOKEN: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    ADMIN_IDS: List[int] = field(default_factory=list)
    API_URL: str = field(default_factory=lambda: os.getenv("API_URL", "http://localhost:8000"))
    WEBAPP_URL: str = field(default_factory=lambda: os.getenv("WEBAPP_URL", ""))
    DATA_DIR: str = field(default_factory=lambda: os.getenv("DATA_DIR", "data"))
    
    def __post_init__(self):
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        if admin_ids_str:
            self.ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
    
    def is_admin(self, user_id: int) -> bool:
        return user_id in self.ADMIN_IDS


config = Config()
