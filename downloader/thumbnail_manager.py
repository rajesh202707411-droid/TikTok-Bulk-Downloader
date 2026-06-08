import os
import glob
import time
import aiohttp
import hashlib
from logger import logger
from settings.config import config_mgr

class ThumbnailManager:
    def __init__(self, cache_dir="cache/thumbnails"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.cleanup_cache()

    def get_cache_path(self, identifier):
        """Generates a stable cache file path based on a URL or Video ID"""
        hash_id = hashlib.md5(identifier.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{hash_id}.jpg")

    def is_cached(self, identifier):
        path = self.get_cache_path(identifier)
        return os.path.exists(path)

    async def fetch_and_cache(self, url, identifier=None):
        if not identifier:
            identifier = url
            
        config = config_mgr.load()
        if not config.get("enable_thumbnail_cache", True):
            # If disabled, we still fetch, but just return bytes without caching
            return await self._fetch_network(url)

        cache_path = self.get_cache_path(identifier)
        
        # Check cache
        if os.path.exists(cache_path):
            try:
                # Update modified time for LRU eviction
                os.utime(cache_path, None)
                with open(cache_path, "rb") as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Failed to read cache {cache_path}: {e}")

        # Fetch and save
        data = await self._fetch_network(url)
        if data:
            try:
                with open(cache_path, "wb") as f:
                    f.write(data)
            except Exception as e:
                logger.error(f"Failed to save thumbnail to cache: {e}")
                
        return data

    async def _fetch_network(self, url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.read()
        except Exception as e:
            logger.error(f"Failed to fetch thumbnail from network: {e}")
        return None

    def cleanup_cache(self):
        """Cleans up cache directory if it exceeds the limit."""
        config = config_mgr.load()
        limit_mb = config.get("thumbnail_cache_limit_mb", 100)
        
        if limit_mb <= 0:
            return

        try:
            files = glob.glob(os.path.join(self.cache_dir, "*.jpg"))
            files.sort(key=os.path.getmtime) # Oldest first
            
            total_size = sum(os.path.getsize(f) for f in files)
            limit_bytes = limit_mb * 1024 * 1024
            
            while total_size > limit_bytes and files:
                oldest = files.pop(0)
                size = os.path.getsize(oldest)
                os.remove(oldest)
                total_size -= size
                logger.info(f"Evicted thumbnail from cache: {oldest}")
        except Exception as e:
            logger.error(f"Thumbnail cache cleanup failed: {e}")

    def clear_all(self):
        """Deletes all cached thumbnails."""
        try:
            files = glob.glob(os.path.join(self.cache_dir, "*.jpg"))
            for f in files:
                os.remove(f)
            logger.info("Cleared all thumbnail cache.")
            return True
        except Exception as e:
            logger.error(f"Failed to clear thumbnail cache: {e}")
            return False

thumbnail_mgr = ThumbnailManager()
