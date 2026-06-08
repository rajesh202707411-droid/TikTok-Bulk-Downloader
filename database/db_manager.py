import sqlite3
import os
from datetime import datetime
from models.download_history import DownloadHistoryItem
from logger import logger

class DBManager:
    def __init__(self, db_path="database/history.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS downloads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT NOT NULL,
                        title TEXT NOT NULL,
                        file_path TEXT,
                        status TEXT NOT NULL,
                        download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                # Migration: Add new columns if they don't exist
                cursor.execute("PRAGMA table_info(downloads)")
                columns = [info[1] for info in cursor.fetchall()]
                
                if "thumbnail_path" not in columns:
                    cursor.execute("ALTER TABLE downloads ADD COLUMN thumbnail_path TEXT")
                if "thumbnail_url" not in columns:
                    cursor.execute("ALTER TABLE downloads ADD COLUMN thumbnail_url TEXT")
                if "cache_status" not in columns:
                    cursor.execute("ALTER TABLE downloads ADD COLUMN cache_status TEXT DEFAULT 'none'")
                if "last_thumbnail_update" not in columns:
                    cursor.execute("ALTER TABLE downloads ADD COLUMN last_thumbnail_update TIMESTAMP")
                if "in_queue" not in columns:
                    cursor.execute("ALTER TABLE downloads ADD COLUMN in_queue BOOLEAN DEFAULT 0")
                if "upload_date" not in columns:
                    cursor.execute("ALTER TABLE downloads ADD COLUMN upload_date TEXT")

                conn.commit()
                logger.info("Database initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    def add_download(self, url, title, file_path, status, thumbnail_path=None, thumbnail_url=None, cache_status="none", in_queue=1, upload_date=None):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO downloads (url, title, file_path, status, download_date, thumbnail_path, thumbnail_url, cache_status, last_thumbnail_update, in_queue, upload_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (url, title, file_path, status, datetime.now(), thumbnail_path, thumbnail_url, cache_status, datetime.now(), in_queue, upload_date))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to add download to db: {e}")
            return None

    def get_all_downloads(self, search_query=""):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if search_query:
                    query = f"%{search_query}%"
                    cursor.execute('''
                        SELECT id, url, title, file_path, status, download_date, thumbnail_path, thumbnail_url, cache_status, last_thumbnail_update, upload_date 
                        FROM downloads 
                        WHERE title LIKE ? OR url LIKE ?
                        ORDER BY download_date DESC
                    ''', (query, query))
                else:
                    cursor.execute('''
                        SELECT id, url, title, file_path, status, download_date, thumbnail_path, thumbnail_url, cache_status, last_thumbnail_update, upload_date 
                        FROM downloads 
                        ORDER BY download_date DESC
                    ''')
                
                rows = cursor.fetchall()
                result = []
                for row in rows:
                    date_obj = datetime.strptime(row[5], '%Y-%m-%d %H:%M:%S.%f') if '.' in row[5] else datetime.strptime(row[5], '%Y-%m-%d %H:%M:%S')
                    
                    # Parse last update if exists
                    last_update = None
                    if row[9]:
                        last_update = datetime.strptime(row[9], '%Y-%m-%d %H:%M:%S.%f') if '.' in row[9] else datetime.strptime(row[9], '%Y-%m-%d %H:%M:%S')
                        
                    item = DownloadHistoryItem(
                        id=row[0],
                        url=row[1],
                        title=row[2],
                        file_path=row[3],
                        status=row[4],
                        download_date=date_obj,
                        thumbnail_path=row[6],
                        thumbnail_url=row[7],
                        cache_status=row[8],
                        last_thumbnail_update=last_update,
                        upload_date=row[10]
                    )
                    result.append(item)
                return result
        except Exception as e:
            logger.error(f"Failed to get downloads from db: {e}")
            return []

    def clear_history(self):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM downloads')
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to clear history: {e}")
            return False

    def add_downloads_bulk(self, items, in_queue=1):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                records = []
                for item in items:
                    now = datetime.now()
                    records.append((
                        item['url'], 
                        item.get('title', 'Bulk Download'), 
                        item.get('file_path', ''), 
                        item['status'], 
                        now, 
                        item.get('thumbnail_path'), 
                        item.get('thumbnail_url'), 
                        item.get('cache_status', 'none'), 
                        now,
                        in_queue,
                        item.get('upload_date')
                    ))
                
                cursor.executemany('''
                    INSERT INTO downloads (url, title, file_path, status, download_date, thumbnail_path, thumbnail_url, cache_status, last_thumbnail_update, in_queue, upload_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', records)
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to add bulk downloads to db: {e}")
            return False

    def get_active_queue(self):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, url, title, file_path, status, download_date, thumbnail_path, thumbnail_url, cache_status, last_thumbnail_update, upload_date 
                    FROM downloads 
                    WHERE in_queue = 1
                    ORDER BY id ASC
                ''')
                rows = cursor.fetchall()
                result = []
                for row in rows:
                    item = {
                        'id': row[0], 'url': row[1], 'title': row[2], 'filename': row[3], 'status': row[4],
                        'thumb_path': row[6], 'thumb_url': row[7], 'progress': 0, 'worker': None, 'upload_date': row[10]
                    }
                    if item['status'] == 'Downloading':
                        item['status'] = 'Queued' # Reset interrupted downloads
                    result.append(item)
                return result
        except Exception as e:
            logger.error(f"Failed to get active queue: {e}")
            return []

    def remove_from_queue_bulk(self, urls):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Use parameterized query with IN clause
                placeholders = ','.join('?' * len(urls))
                cursor.execute(f'UPDATE downloads SET in_queue = 0 WHERE url IN ({placeholders})', urls)
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to remove from queue: {e}")
            return False

    def clear_queue_by_status(self, statuses):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if statuses:
                    placeholders = ','.join('?' * len(statuses))
                    cursor.execute(f'UPDATE downloads SET in_queue = 0 WHERE status IN ({placeholders}) AND in_queue = 1', statuses)
                else:
                    # Clear all if statuses is empty
                    cursor.execute('UPDATE downloads SET in_queue = 0 WHERE in_queue = 1')
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to clear queue by status: {e}")
            return False

    def update_download_status(self, url, status):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE downloads SET status = ? WHERE url = ? AND in_queue = 1', (status, url))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to update download status: {e}")
            return False
