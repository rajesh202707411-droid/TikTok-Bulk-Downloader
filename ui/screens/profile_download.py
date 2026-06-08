from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QListWidget, QListWidgetItem, QListView, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QSize, QRect
from PySide6.QtGui import QIcon, QPixmap, QImage, QPainter, QPainterPath
from workers.download_worker import ProfileExtractorWorker, ThumbnailLoaderWorker
from utils import extract_date_from_info
import math

class ProfileDownloadScreen(QWidget):
    send_to_bulk = Signal(list)
    
    def __init__(self):
        super().__init__()
        self.videos = []
        self.workers = {} # Track thumbnail workers
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Profile Download")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        layout.addWidget(title)

        input_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste TikTok Profile URL here (e.g. @username)...")
        self.url_input.setStyleSheet("padding: 10px; font-size: 14px;")
        
        self.analyze_btn = QPushButton("Analyze Profile")
        self.analyze_btn.setStyleSheet("padding: 10px 20px; font-size: 14px;")
        self.analyze_btn.clicked.connect(self.analyze_profile)
        
        input_layout.addWidget(self.url_input)
        input_layout.addWidget(self.analyze_btn)
        layout.addLayout(input_layout)

        self.stats_label = QLabel("Videos found: 0")
        self.stats_label.setStyleSheet("font-size: 14px; color: #b3b3b3;")
        layout.addWidget(self.stats_label)

        # List Widget as Grid
        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListView.IconMode)
        self.list_widget.setResizeMode(QListView.Adjust)
        self.list_widget.setSpacing(10)
        self.list_widget.setIconSize(QSize(150, 200))
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #121212;
                border: 1px solid #2c2c2c;
                outline: none;
            }
            QListWidget::item {
                color: white;
                border-radius: 8px;
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #2c2c2c;
            }
        """)
        self.list_widget.verticalScrollBar().valueChanged.connect(self.load_visible_thumbnails)
        layout.addWidget(self.list_widget)

        actions_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all)
        
        self.deselect_all_btn = QPushButton("Deselect All")
        self.deselect_all_btn.clicked.connect(self.deselect_all)
        
        self.download_btn = QPushButton("Add to Bulk Download")
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #00f2fe;
                color: black;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #00c2cb;
            }
        """)
        self.download_btn.clicked.connect(self.add_to_bulk)
        
        actions_layout.addWidget(self.select_all_btn)
        actions_layout.addWidget(self.deselect_all_btn)
        actions_layout.addStretch()
        actions_layout.addWidget(self.download_btn)
        layout.addLayout(actions_layout)

    def analyze_profile(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a profile URL")
            return
            
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("Fetching...")
        self.list_widget.clear()
        
        # Stop existing workers
        for worker in self.workers.values():
            worker.quit()
        self.workers.clear()
        
        self.worker = ProfileExtractorWorker(url)
        self.worker.finished.connect(self.on_fetch_finished)
        self.worker.error.connect(self.on_fetch_error)
        self.worker.start()

    def on_fetch_finished(self, videos):
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Analyze Profile")
        self.videos = videos
        self.stats_label.setText(f"Videos found: {len(videos)}")
        
        placeholder = self.create_placeholder_icon()
        
        for index, video in enumerate(videos):
            title = video.get('title', 'Unknown Title')
            # Shorten title
            if len(title) > 20:
                title = title[:17] + "..."
                
            duration = video.get('duration', 0)
            mins, secs = divmod(duration, 60)
            
            date_str = extract_date_from_info(video)
                
            item_text = f"{title}\nDuration: {mins}:{secs:02d}\nUploaded: {date_str}"
            
            item = QListWidgetItem(placeholder, item_text)
            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item.setCheckState(Qt.Checked)
            
            # Store data
            item.setData(Qt.UserRole, index)
            self.list_widget.addItem(item)
            
        # Initial load
        self.load_visible_thumbnails()

    def on_fetch_error(self, error_msg):
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Analyze Profile")
        QMessageBox.critical(self, "Error", f"Failed to fetch profile:\n{error_msg}")

    def create_placeholder_icon(self):
        pixmap = QPixmap(150, 200)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        path = QPainterPath()
        path.addRoundedRect(0, 0, 150, 200, 8, 8)
        
        painter.fillPath(path, Qt.darkGray)
        painter.setPen(Qt.white)
        painter.drawText(QRect(0, 0, 150, 200), Qt.AlignCenter, "Loading...")
        painter.end()
        return QIcon(pixmap)

    def load_visible_thumbnails(self):
        viewport = self.list_widget.viewport()
        rect = viewport.rect()
        
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item_rect = self.list_widget.visualItemRect(item)
            
            if item_rect.intersects(rect):
                index = item.data(Qt.UserRole)
                self.start_thumbnail_worker(index, item)

    def start_thumbnail_worker(self, index, item):
        if index in self.workers:
            return # Already loading or loaded
            
        video = self.videos[index]
        vid_id = video.get('id', str(index))
        
        from logger import logger
        logger.debug(f"[Profile] Video fetched: {vid_id} - {video.get('title', 'Unknown')}")
        
        thumb_url = video.get('thumbnail')
        if not thumb_url and video.get('thumbnails'):
            thumbnails = video.get('thumbnails')
            if isinstance(thumbnails, list) and len(thumbnails) > 0:
                thumb_url = thumbnails[-1].get('url')
                
        logger.debug(f"[Profile] Thumbnail URL extracted: {thumb_url}")
        
        if not thumb_url:
            logger.debug(f"[Profile] Thumbnail load failed (no URL found) for {vid_id}")
            return
            
        from downloader.thumbnail_manager import thumbnail_mgr
        if thumbnail_mgr.is_cached(vid_id):
            logger.debug(f"[Profile] Thumbnail cache hit for {vid_id}")
        else:
            logger.debug(f"[Profile] Thumbnail download started for {vid_id}")
            
        worker = ThumbnailLoaderWorker(thumb_url, vid_id)
        worker.finished.connect(lambda data, id_: self.on_thumbnail_loaded(index, item, data))
        worker.error.connect(lambda msg: self.on_thumbnail_error(index, vid_id, msg))
        self.workers[index] = worker
        worker.start()

    def on_thumbnail_loaded(self, index, item, data):
        from logger import logger
        video = self.videos[index]
        vid_id = video.get('id', str(index))
        logger.debug(f"[Profile] Thumbnail download success for {vid_id}")
        logger.debug(f"[Profile] Thumbnail assigned to card")
        image = QImage()
        image.loadFromData(data)
        
        pixmap = QPixmap(image).scaled(150, 200, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        
        # Rounded corners
        rounded = QPixmap(150, 200)
        rounded.fill(Qt.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, 150, 200, 8, 8)
        painter.setClipPath(path)
        x = (150 - pixmap.width()) // 2
        y = (200 - pixmap.height()) // 2
        painter.drawPixmap(x, y, pixmap)
        painter.end()
        
        item.setIcon(QIcon(rounded))

    def on_thumbnail_error(self, index, vid_id, msg):
        from logger import logger
        logger.debug(f"[Profile] Thumbnail load failed for {vid_id}: {msg}")

    def select_all(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.Checked)

    def deselect_all(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.Unchecked)

    def add_to_bulk(self):
        selected_urls = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                index = item.data(Qt.UserRole)
                video = self.videos[index]
                url = video.get('url') or video.get('webpage_url')
                if url:
                    selected_urls.append(url)
                            
        if not selected_urls:
            QMessageBox.warning(self, "Warning", "No videos selected.")
            return
            
        self.send_to_bulk.emit(selected_urls)
        QMessageBox.information(self, "Success", f"Sent {len(selected_urls)} videos to Bulk Download queue.")
