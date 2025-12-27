"""Bot configuration."""
import os
import logging
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


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
            try:
                self.ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip().isdigit()]
            except ValueError as e:
                logger.error(f"Invalid ADMIN_IDS format: {e}")
                self.ADMIN_IDS = []
    
    def is_admin(self, user_id: int) -> bool:
        return user_id in self.ADMIN_IDS
    
    def validate(self) -> bool:
        """Validate required configuration."""
        if not self.BOT_TOKEN or self.BOT_TOKEN == "your_bot_token_here":
            logger.error("BOT_TOKEN is not configured")
            return False
        return True


config = Config()
