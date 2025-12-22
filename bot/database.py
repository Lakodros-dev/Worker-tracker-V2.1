"""Simple JSON database for bot."""
import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
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
