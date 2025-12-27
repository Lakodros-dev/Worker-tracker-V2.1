"""Simple JSON database for bot."""
import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from config import config

logger = logging.getLogger(__name__)


class JsonDB:
    """Async-safe JSON database."""
    
    _locks: Dict[str, asyncio.Lock] = {}
    _sync_lock = asyncio.Lock()
    
    def __init__(self):
        self.data_dir = Path(config.DATA_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    async def _get_lock(self, filename: str) -> asyncio.Lock:
        async with self._sync_lock:
            if filename not in self._locks:
                self._locks[filename] = asyncio.Lock()
            return self._locks[filename]
    
    def _filepath(self, filename: str) -> Path:
        return self.data_dir / filename
    
    async def read(self, filename: str) -> List[Dict]:
        filepath = self._filepath(filename)
        lock = await self._get_lock(filename)
        async with lock:
            if not filepath.exists():
                return []
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error in {filename}: {e}")
                return []
            except IOError as e:
                logger.error(f"IO error reading {filename}: {e}")
                return []
    
    async def write(self, filename: str, data: List[Dict]) -> bool:
        filepath = self._filepath(filename)
        lock = await self._get_lock(filename)
        async with lock:
            try:
                # Atomic write: write to temp file first
                temp_path = filepath.with_suffix('.tmp')
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                temp_path.replace(filepath)
                return True
            except IOError as e:
                logger.error(f"IO error writing {filename}: {e}")
                return False
    
    async def append(self, filename: str, item: Dict) -> bool:
        filepath = self._filepath(filename)
        lock = await self._get_lock(filename)
        async with lock:
            try:
                # Read inside lock to prevent race condition
                if not filepath.exists():
                    data = []
                else:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                
                data.append(item)
                
                temp_path = filepath.with_suffix('.tmp')
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                temp_path.replace(filepath)
                return True
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error appending to {filename}: {e}")
                return False
    
    async def find_one(self, filename: str, key: str, value: Any) -> Optional[Dict]:
        data = await self.read(filename)
        for item in data:
            if item.get(key) == value:
                return item
        return None
    
    async def update(self, filename: str, key: str, value: Any, updates: Dict) -> bool:
        filepath = self._filepath(filename)
        lock = await self._get_lock(filename)
        async with lock:
            try:
                if not filepath.exists():
                    return False
                
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                found = False
                for item in data:
                    if item.get(key) == value:
                        item.update(updates)
                        found = True
                        break
                
                if not found:
                    return False
                
                temp_path = filepath.with_suffix('.tmp')
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                temp_path.replace(filepath)
                return True
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error updating {filename}: {e}")
                return False
    
    async def find_many(self, filename: str, filters: Dict) -> List[Dict]:
        data = await self.read(filename)
        return [item for item in data if all(item.get(k) == v for k, v in filters.items())]
    
    async def count(self, filename: str, filters: Optional[Dict] = None) -> int:
        """Count items, optionally filtered."""
        data = await self.read(filename)
        if filters is None:
            return len(data)
        return len([item for item in data if all(item.get(k) == v for k, v in filters.items())])


db = JsonDB()
