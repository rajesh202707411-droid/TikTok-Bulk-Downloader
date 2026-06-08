import asyncio
import yt_dlp
import os
from logger import logger
from settings.config import config_mgr

class YTDLPEngine:
    def __init__(self):
        config = config_mgr.load()
        self.download_dir = config.get("download_dir", "downloads")
        os.makedirs(self.download_dir, exist_ok=True)
    
    def get_base_options(self):
        return {
            'outtmpl': os.path.join(self.download_dir, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            # TikTok specific headers sometimes help
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            }
        }
    
    async def extract_info(self, url):
        """Asynchronously extracts metadata without downloading"""
        logger.info(f"Extracting info for URL: {url}")
        ydl_opts = self.get_base_options()
        ydl_opts['extract_flat'] = False
        ydl_opts['skip_download'] = True
        
        loop = asyncio.get_event_loop()
        
        def _extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
                
        try:
            # Run the synchronous yt_dlp call in a thread pool to avoid blocking the asyncio event loop
            info = await loop.run_in_executor(None, _extract)
            return info
        except Exception as e:
            logger.error(f"Error extracting info for {url}: {e}")
            raise

    async def fetch_profile_videos(self, profile_url):
        """Asynchronously extracts a list of videos from a TikTok profile"""
        logger.info(f"Extracting profile videos for: {profile_url}")
        ydl_opts = self.get_base_options()
        ydl_opts['extract_flat'] = True  # We only need metadata for the list
        ydl_opts['skip_download'] = True
        
        loop = asyncio.get_event_loop()
        
        def _extract_profile():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(profile_url, download=False)
                
        try:
            info = await loop.run_in_executor(None, _extract_profile)
            if info and 'entries' in info:
                return list(info['entries'])
            return []
        except Exception as e:
            logger.error(f"Error extracting profile {profile_url}: {e}")
            raise

    async def download_video(self, url, progress_callback=None, quality='best'):
        """Asynchronously downloads a video with given quality"""
        logger.info(f"Starting download for {url} with quality {quality}")
        ydl_opts = self.get_base_options()
        
        if quality == 'audio':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        elif quality == 'sd':
            ydl_opts['format'] = 'worst[ext=mp4]/worst'
        else:
            ydl_opts['format'] = 'best[ext=mp4]/best'
            
        def ydl_hook(d):
            if progress_callback:
                if d['status'] == 'downloading':
                    total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    downloaded_bytes = d.get('downloaded_bytes', 0)
                    if total_bytes > 0:
                        percent = (downloaded_bytes / total_bytes) * 100
                        speed = d.get('speed', 0)
                        eta = d.get('eta', 0)
                        progress_callback({
                            'status': 'downloading',
                            'percent': percent,
                            'speed': speed,
                            'eta': eta,
                            'filename': d.get('filename', '')
                        })
                elif d['status'] == 'finished':
                    progress_callback({
                        'status': 'finished',
                        'percent': 100,
                        'filename': d.get('filename', '')
                    })

        ydl_opts['progress_hooks'] = [ydl_hook]
        
        loop = asyncio.get_event_loop()
        
        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
        try:
            await loop.run_in_executor(None, _download)
            logger.info(f"Download completed for {url}")
            return True
        except Exception as e:
            logger.error(f"Download failed for {url}: {e}")
            raise
