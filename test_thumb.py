import asyncio
from downloader.yt_dlp_engine import YTDLPEngine
from downloader.thumbnail_manager import thumbnail_mgr
import os

async def test_thumbnail():
    url = "https://www.tiktok.com/@tiktok/video/7106594312292453675"
    engine = YTDLPEngine()
    
    print("Extracting metadata...")
    info = await engine.extract_info(url)
    
    thumb_url = info.get('thumbnail')
    if not thumb_url:
        print("No thumbnail URL found in metadata!")
        return
        
    print(f"Thumbnail URL found: {thumb_url}")
    
    vid_id = info.get('id', 'test_vid')
    
    print("Fetching and caching thumbnail...")
    data = await thumbnail_mgr.fetch_and_cache(thumb_url, vid_id)
    
    if data:
        print(f"Thumbnail downloaded successfully. Size: {len(data)} bytes")
        
        # Check cache file
        cache_path = thumbnail_mgr.get_cache_path(vid_id)
        if os.path.exists(cache_path):
            print(f"Cache file exists at: {cache_path}")
            print(f"Cache file size: {os.path.getsize(cache_path)} bytes")
        else:
            print("Cache file does NOT exist!")
    else:
        print("Thumbnail download failed! Data is None.")

if __name__ == "__main__":
    asyncio.run(test_thumbnail())
