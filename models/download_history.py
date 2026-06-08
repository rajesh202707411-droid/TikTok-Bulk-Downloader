from dataclasses import dataclass
from datetime import datetime

@dataclass
class DownloadHistoryItem:
    url: str
    title: str
    file_path: str
    status: str
    download_date: datetime
    id: int = None
    thumbnail_path: str = None
    thumbnail_url: str = None
    cache_status: str = "none"
    last_thumbnail_update: datetime = None
    upload_date: str = None
