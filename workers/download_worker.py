import asyncio
import aiohttp
import os
import hashlib
from PySide6.QtCore import QThread, Signal
from downloader.yt_dlp_engine import YTDLPEngine
from downloader.thumbnail_manager import thumbnail_mgr
from logger import logger

class InfoExtractorWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url
        self.engine = YTDLPEngine()

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Fetch metadata
            info = loop.run_until_complete(self.engine.extract_info(self.url))
            
            # Optionally fetch thumbnail bytes if thumbnail URL is present
            thumbnail_bytes = None
            if info and info.get('thumbnail'):
                vid_id = info.get('id', self.url)
                thumbnail_bytes = loop.run_until_complete(thumbnail_mgr.fetch_and_cache(info['thumbnail'], vid_id))
                info['thumbnail_bytes'] = thumbnail_bytes
                
            self.finished.emit(info)
        except Exception as e:
            logger.error(f"Info extractor failed: {str(e)}")
            self.error.emit(str(e))
        finally:
            loop.close()

class DownloadWorker(QThread):
    progress = Signal(dict)
    finished = Signal(bool)
    error = Signal(str)

    def __init__(self, url, quality):
        super().__init__()
        self.url = url
        self.quality = quality
        self.engine = YTDLPEngine()

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            def progress_callback(data):
                self.progress.emit(data)
                
            success = loop.run_until_complete(
                self.engine.download_video(self.url, progress_callback, self.quality)
            )
            self.finished.emit(success)
        except Exception as e:
            logger.error(f"Download failed: {str(e)}")
            self.error.emit(str(e))
        finally:
            loop.close()

class ProfileExtractorWorker(QThread):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, profile_url):
        super().__init__()
        self.profile_url = profile_url
        self.engine = YTDLPEngine()

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            videos = loop.run_until_complete(self.engine.fetch_profile_videos(self.profile_url))
            self.finished.emit(videos)
        except Exception as e:
            logger.error(f"Profile extractor failed: {str(e)}")
            self.error.emit(str(e))
        finally:
            loop.close()


class ThumbnailLoaderWorker(QThread):
    finished = Signal(bytes, str) # Emits (image_bytes, url/id)
    error = Signal(str)

    def __init__(self, url, identifier=None):
        super().__init__()
        self.url = url
        self.identifier = identifier or url

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            data = loop.run_until_complete(thumbnail_mgr.fetch_and_cache(self.url, self.identifier))
            if data:
                self.finished.emit(data, self.identifier)
            else:
                self.error.emit("Failed to fetch")
        except Exception as e:
            logger.error(f"ThumbnailLoaderWorker failed: {str(e)}")
            self.error.emit(str(e))
        finally:
            loop.close()


