import datetime
from logger import logger

def extract_date_from_info(info):
    """
    Extracts and formats the upload date from yt-dlp info metadata.
    Prioritizes upload_date, falls back to various timestamp fields.
    Returns the formatted 'YYYY-MM-DD' string or 'Date Unavailable'.
    """
    upload_date = info.get('upload_date')
    timestamp = (info.get('timestamp') or 
                 info.get('release_timestamp') or 
                 info.get('created_time') or 
                 info.get('create_time') or 
                 info.get('publish_time'))
    
    date_str = "Date Unavailable"
    
    if upload_date and len(str(upload_date)) >= 8:
        upload_date = str(upload_date)
        # Format YYYYMMDD to YYYY-MM-DD
        date_str = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
        logger.debug(f"[Date] upload_date found: {upload_date} -> converted to {date_str}")
    elif timestamp:
        logger.debug(f"[Date] timestamp fallback used: {timestamp}")
        try:
            date_str = datetime.datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d')
            logger.debug(f"[Date] date converted successfully: {date_str}")
        except Exception as e:
            logger.debug(f"[Date] no date available (timestamp conversion failed: {e})")
    else:
        logger.debug("[Date] no date available")
        
    return date_str
