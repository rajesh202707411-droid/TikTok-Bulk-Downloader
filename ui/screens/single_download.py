from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QProgressBar, QComboBox, QFrame, QMessageBox, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap, QImage, QPainter, QPainterPath, QBrush
from workers.download_worker import InfoExtractorWorker, DownloadWorker
from database.db_manager import DBManager
from utils import extract_date_from_info

class SingleDownloadScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.current_url = None
        self.current_title = "Unknown"
        self.current_filename = ""
        self.db = DBManager()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title = QLabel("Single Video Download")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        layout.addWidget(title)

        # Input Area
        input_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste TikTok URL here...")
        self.url_input.setStyleSheet("padding: 10px; font-size: 14px;")
        
        self.analyze_btn = QPushButton("Analyze")
        self.analyze_btn.setStyleSheet("padding: 10px 20px; font-size: 14px;")
        self.analyze_btn.clicked.connect(self.analyze_url)
        
        input_layout.addWidget(self.url_input)
        input_layout.addWidget(self.analyze_btn)
        layout.addLayout(input_layout)

        # Content Area (Thumbnail + Info)
        self.content_frame = QFrame()
        self.content_frame.setVisible(False) # Hidden initially
        content_layout = QHBoxLayout(self.content_frame)
        
        # Thumbnail
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(200, 260)
        self.thumbnail_label.setStyleSheet("background-color: #2c2c2c; border-radius: 8px;")
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setText("Loading...")
        
        # Setup opacity effect for animation
        self.opacity_effect = QGraphicsOpacityEffect()
        self.thumbnail_label.setGraphicsEffect(self.opacity_effect)
        
        # Info
        info_layout = QVBoxLayout()
        self.info_title = QLabel("Title: ")
        self.info_title.setWordWrap(True)
        self.info_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        
        self.info_author = QLabel("Author: ")
        self.info_author.setStyleSheet("font-size: 14px; color: #b3b3b3;")
        
        self.info_duration = QLabel("Duration: ")
        self.info_duration.setStyleSheet("font-size: 14px; color: #b3b3b3;")
        
        self.info_date = QLabel("Uploaded: ")
        self.info_date.setStyleSheet("font-size: 14px; color: #b3b3b3;")
        
        # Quality Selector
        quality_layout = QHBoxLayout()
        quality_label = QLabel("Quality:")
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Video HD (Best)", "Video SD (Worst)", "Audio Only"])
        quality_layout.addWidget(quality_label)
        quality_layout.addWidget(self.quality_combo)
        quality_layout.addStretch()
        
        # Download Button
        self.download_btn = QPushButton("Download")
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #fe0979;
                color: white;
                font-weight: bold;
                padding: 12px;
                font-size: 16px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #d10763;
            }
        """)
        self.download_btn.clicked.connect(self.start_download)
        
        info_layout.addWidget(self.info_title)
        info_layout.addWidget(self.info_author)
        info_layout.addWidget(self.info_duration)
        info_layout.addWidget(self.info_date)
        info_layout.addLayout(quality_layout)
        info_layout.addWidget(self.download_btn)
        info_layout.addStretch()
        
        content_layout.addWidget(self.thumbnail_label)
        content_layout.addLayout(info_layout)
        
        layout.addWidget(self.content_frame)

        # Progress Area
        self.progress_frame = QFrame()
        self.progress_frame.setVisible(False)
        progress_layout = QVBoxLayout(self.progress_frame)
        
        self.status_label = QLabel("Waiting...")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #2c2c2c;
                border-radius: 5px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #00f2fe;
                width: 10px;
            }
        """)
        
        progress_layout.addWidget(self.status_label)
        progress_layout.addWidget(self.progress_bar)
        
        layout.addWidget(self.progress_frame)
        layout.addStretch()

    def analyze_url(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a valid URL")
            return
            
        self.current_url = url
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("Analyzing...")
        
        # Start worker
        self.extractor_worker = InfoExtractorWorker(url)
        self.extractor_worker.finished.connect(self.on_analyze_finished)
        self.extractor_worker.error.connect(self.on_analyze_error)
        self.extractor_worker.start()

    def on_analyze_finished(self, info):
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Analyze")
        
        if not info:
            QMessageBox.warning(self, "Error", "Failed to extract video info")
            return
            
        self.current_title = info.get('title', 'Unknown')
        
        # Update UI
        self.info_title.setText(f"Title: {self.current_title}")
        self.info_author.setText(f"Author: {info.get('uploader', info.get('uploader_id', 'Unknown'))}")
        
        duration = info.get('duration')
        if duration:
            mins, secs = divmod(duration, 60)
            self.info_duration.setText(f"Duration: {mins}:{secs:02d}")
            
        self.current_upload_date = extract_date_from_info(info)
        self.info_date.setText(f"Uploaded: {self.current_upload_date}")
            
        # Set thumbnail with rounded corners
        thumbnail_bytes = info.get('thumbnail_bytes')
        if thumbnail_bytes:
            image = QImage()
            image.loadFromData(thumbnail_bytes)
            pixmap = QPixmap(image).scaled(200, 260, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            
            # Apply rounded corners
            rounded = QPixmap(200, 260)
            rounded.fill(Qt.transparent)
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.Antialiasing)
            path = QPainterPath()
            path.addRoundedRect(0, 0, 200, 260, 8, 8)
            painter.setClipPath(path)
            
            # Center the pixmap
            x = (200 - pixmap.width()) // 2
            y = (260 - pixmap.height()) // 2
            painter.drawPixmap(x, y, pixmap)
            painter.end()
            
            self.thumbnail_label.setPixmap(rounded)
            
            # Fade-in animation
            self.opacity_effect.setOpacity(0)
            self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
            self.anim.setDuration(500)
            self.anim.setStartValue(0)
            self.anim.setEndValue(1)
            self.anim.setEasingCurve(QEasingCurve.InOutQuad)
            self.anim.start()
        else:
            self.thumbnail_label.setText("No Thumbnail")
            
        self.content_frame.setVisible(True)

    def on_analyze_error(self, error_msg):
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Analyze")
        QMessageBox.critical(self, "Error", f"Could not analyze URL:\n{error_msg}")

    def start_download(self):
        if not self.current_url:
            return
            
        # Determine quality
        idx = self.quality_combo.currentIndex()
        quality_map = {0: 'best', 1: 'sd', 2: 'audio'}
        selected_quality = quality_map.get(idx, 'best')
        
        self.download_btn.setEnabled(False)
        self.progress_frame.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting download...")
        
        self.download_worker = DownloadWorker(self.current_url, selected_quality)
        self.download_worker.progress.connect(self.on_download_progress)
        self.download_worker.finished.connect(self.on_download_finished)
        self.download_worker.error.connect(self.on_download_error)
        self.download_worker.start()

    def on_download_progress(self, data):
        if data['status'] == 'downloading':
            self.progress_bar.setValue(int(data['percent']))
            self.status_label.setText(f"Downloading... {data['percent']:.1f}%")
        elif data['status'] == 'finished':
            self.progress_bar.setValue(100)
            self.current_filename = data.get('filename', '')
            self.status_label.setText("Processing finished...")

    def on_download_finished(self, success):
        self.download_btn.setEnabled(True)
        status_str = "Completed" if success else "Failed"
        self.db.add_download(self.current_url, self.current_title, self.current_filename, status_str, upload_date=getattr(self, 'current_upload_date', None))
        
        if success:
            self.status_label.setText("Download Complete!")
            QMessageBox.information(self, "Success", "Video downloaded successfully!")
        else:
            self.status_label.setText("Download Failed.")

    def on_download_error(self, error_msg):
        self.download_btn.setEnabled(True)
        self.status_label.setText("Error occurred.")
        QMessageBox.critical(self, "Error", f"Download failed:\n{error_msg}")
