"""JSON Database for backend."""
import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from config import config


class JsonDB:
    """Thread-safe JSON database."""
    
    _locks: Dict[str, threading.Lock] = {}
    _global_lock = threading.Lock()
    
    def __init__(self):
        self.data_dir = Path(config.DATA_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_lock(self, filename: str) -> threading.Lock:
        with self._global_lock:
            if filename not in self._locks:
                self._locks[filename] = threading.Lock()
            return self._locks[filename]
    
    def _filepath(self, filename: str) -> Path:
        return self.data_dir / filename
    
    def read(self, filename: str) -> List[Dict]:
        filepath = self._filepath(filename)
        lock = self._get_lock(filename)
        with lock:
            if not filepath.exists():
                return []
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return []
    
    def write(self, filename: str, data: List[Dict]) -> bool:
        filepath = self._filepath(filename)
        lock = self._get_lock(filename)
        with lock:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return True
            except:
                return False
    
    def read_single(self, filename: str) -> Optional[Dict]:
        filepath = self._filepath(filename)
        lock = self._get_lock(filename)
        with lock:
            if not filepath.exists():
                return None
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return None
    
    def write_single(self, filename: str, data: Dict) -> bool:
        filepath = self._filepath(filename)
        lock = self._get_lock(filename)
        with lock:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return True
            except:
                return False
    
    def append(self, filename: str, item: Dict) -> bool:
        data = self.read(filename)
        data.append(item)
        return self.write(filename, data)
    
    def find_one(self, filename: str, key: str, value: Any) -> Optional[Dict]:
        data = self.read(filename)
        for item in data:
            if item.get(key) == value:
                return item
        return None
    
    def update(self, filename: str, key: str, value: Any, updates: Dict) -> bool:
        data = self.read(filename)
        for item in data:
            if item.get(key) == value:
                item.update(updates)
                return self.write(filename, data)
        return False
    
    def find_many(self, filename: str, filters: Dict) -> List[Dict]:
        data = self.read(filename)
        return [item for item in data if all(item.get(k) == v for k, v in filters.items())]


db = JsonDB()

# File names
USERS_FILE = "users.json"
SESSIONS_FILE = "sessions.json"
LOCATIONS_FILE = "locations.json"
REPORTS_FILE = "reports.json"
SETTINGS_FILE = "settings.json"


def get_default_settings() -> Dict:
    return {
        "work_start": "09:00",
        "work_end": "18:00",
        "lunch_start": "13:00",
        "lunch_end": "14:00",
        "geofence": {
            "center_lat": 41.311081,
            "center_lng": 69.240562,
            "radius_meters": 100
        }
    }


def get_settings() -> Dict:
    settings = db.read_single(SETTINGS_FILE)
    if not settings:
        settings = get_default_settings()
        db.write_single(SETTINGS_FILE, settings)
    return settings


def save_settings(settings: Dict) -> bool:
    settings["updated_at"] = datetime.now().isoformat()
    return db.write_single(SETTINGS_FILE, settings)
