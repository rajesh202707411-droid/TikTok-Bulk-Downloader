import json
import os

CONFIG_FILE = "settings/config.json"

DEFAULT_CONFIG = {
    "download_dir": "downloads",
    "max_concurrent": 2,
    "auto_retry": 3,
    "enable_thumbnail_cache": True,
    "thumbnail_cache_limit_mb": 100
}

class ConfigManager:
    @staticmethod
    def _ensure_dir():
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        
    @staticmethod
    def load():
        ConfigManager._ensure_dir()
        if not os.path.exists(CONFIG_FILE):
            ConfigManager.save(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
            
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Merge with defaults in case of missing keys
                for k, v in DEFAULT_CONFIG.items():
                    if k not in config:
                        config[k] = v
                return config
        except Exception:
            return DEFAULT_CONFIG.copy()
            
    @staticmethod
    def save(config_dict):
        ConfigManager._ensure_dir()
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=4)
        except Exception as e:
            from logger import logger
            logger.error(f"Failed to save config: {e}")
            
config_mgr = ConfigManager()
