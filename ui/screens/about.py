from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QScrollArea, QPushButton, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, QUrl
from PySide6.QtGui import QFont, QDesktopServices, QPainter, QPainterPath, QLinearGradient, QColor, QPen
import sys


class GlowingFrame(QFrame):
    """A frame with a subtle animated glow border effect."""
    def __init__(self, glow_color="#00f2fe", parent=None):
        super().__init__(parent)
        self._glow_opacity = 0.3
        self._glow_color = QColor(glow_color)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._pulse)
        self._increasing = True
        self._timer.start(50)

    def _pulse(self):
        if self._increasing:
            self._glow_opacity += 0.01
            if self._glow_opacity >= 0.7:
                self._increasing = False
        else:
            self._glow_opacity -= 0.01
            if self._glow_opacity <= 0.2:
                self._increasing = True
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        color = QColor(self._glow_color)
        color.setAlphaF(self._glow_opacity)
        
        pen = QPen(color, 1.5)
        painter.setPen(pen)
        
        path = QPainterPath()
        path.addRoundedRect(1, 1, self.width() - 2, self.height() - 2, 12, 12)
        painter.drawPath(path)
        painter.end()


class AboutScreen(QWidget):
    VERSION = "1.0.0"
    APP_NAME = "TikTok Video Downloader"
    
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        # Main scroll area for the whole page
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)

        # ── Header Section ──────────────────────────────────────────────
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a2e, stop:0.5 #16213e, stop:1 #0f3460);
                border-radius: 16px;
                border: 1px solid #2c2c2c;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(30, 35, 30, 35)
        header_layout.setSpacing(10)

        # App icon text (emoji-style)
        icon_label = QLabel("⬇")
        icon_label.setStyleSheet("font-size: 48px; border: none; background: transparent;")
        icon_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(icon_label)

        # App name
        name_label = QLabel(self.APP_NAME)
        name_label.setFont(QFont("Segoe UI", 28, QFont.Bold))
        name_label.setStyleSheet("color: white; border: none; background: transparent;")
        name_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(name_label)

        # Version badge
        version_label = QLabel(f"v{self.VERSION}")
        version_label.setStyleSheet("""
            color: #00f2fe; 
            font-size: 14px; 
            font-weight: bold;
            background-color: rgba(0, 242, 254, 0.1);
            border: 1px solid rgba(0, 242, 254, 0.3);
            border-radius: 10px;
            padding: 4px 16px;
        """)
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setFixedWidth(80)
        
        version_container = QHBoxLayout()
        version_container.addStretch()
        version_container.addWidget(version_label)
        version_container.addStretch()
        header_layout.addLayout(version_container)

        # Tagline
        tagline = QLabel("Download TikTok videos with ease — single, bulk, or full profiles.")
        tagline.setStyleSheet("color: #b3b3b3; font-size: 14px; border: none; background: transparent;")
        tagline.setAlignment(Qt.AlignCenter)
        tagline.setWordWrap(True)
        header_layout.addWidget(tagline)

        layout.addWidget(header_frame)

        # ── Features Section ────────────────────────────────────────────
        features_title = QLabel("Features")
        features_title.setStyleSheet("font-size: 20px; font-weight: bold; color: white; margin-top: 10px;")
        layout.addWidget(features_title)

        features_grid = QHBoxLayout()
        features_grid.setSpacing(15)

        features = [
            ("🎬", "Single Download", "Download individual TikTok videos by pasting a URL. Choose quality and format."),
            ("👤", "Profile Scraper", "Extract all videos from any TikTok profile and send them to bulk download."),
            ("📦", "Bulk Download", "Queue hundreds of videos and download them concurrently with progress tracking."),
            ("📊", "Download History", "Track all your downloads with search, export to CSV, and thumbnail previews."),
            ("🖼", "Smart Thumbnails", "Automatic thumbnail caching with LRU eviction and configurable cache limits."),
            ("📋", "Clipboard Monitor", "Auto-detects TikTok URLs from your clipboard and offers instant download."),
        ]

        # Two rows of three cards
        col1 = QVBoxLayout()
        col2 = QVBoxLayout()
        col3 = QVBoxLayout()
        columns = [col1, col2, col3]

        for i, (icon, title, desc) in enumerate(features):
            card = self._create_feature_card(icon, title, desc)
            columns[i % 3].addWidget(card)

        for col in columns:
            col.addStretch()
            features_grid.addLayout(col)

        layout.addLayout(features_grid)

        # ── Tech Stack Section ──────────────────────────────────────────
        tech_title = QLabel("Built With")
        tech_title.setStyleSheet("font-size: 20px; font-weight: bold; color: white; margin-top: 10px;")
        layout.addWidget(tech_title)

        tech_frame = QFrame()
        tech_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border-radius: 12px;
                border: 1px solid #2c2c2c;
            }
        """)
        tech_layout = QHBoxLayout(tech_frame)
        tech_layout.setContentsMargins(20, 20, 20, 20)
        tech_layout.setSpacing(20)

        tech_items = [
            ("Python", f"{sys.version_info.major}.{sys.version_info.minor}"),
            ("PySide6", "Qt for Python"),
            ("yt-dlp", "Video Engine"),
            ("SQLite", "Database"),
            ("aiohttp", "Async HTTP"),
        ]

        for name, detail in tech_items:
            tech_chip = self._create_tech_chip(name, detail)
            tech_layout.addWidget(tech_chip)
        tech_layout.addStretch()

        layout.addWidget(tech_frame)

        # ── Keyboard Shortcuts Section ──────────────────────────────────
        shortcuts_title = QLabel("Tips & Info")
        shortcuts_title.setStyleSheet("font-size: 20px; font-weight: bold; color: white; margin-top: 10px;")
        layout.addWidget(shortcuts_title)

        tips_frame = QFrame()
        tips_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border-radius: 12px;
                border: 1px solid #2c2c2c;
            }
        """)
        tips_layout = QVBoxLayout(tips_frame)
        tips_layout.setContentsMargins(20, 20, 20, 20)
        tips_layout.setSpacing(8)

        tips = [
            "Copy a TikTok URL and the app will auto-detect it from your clipboard.",
            "Use Profile Download to scrape all videos from a creator, then send them to Bulk Download.",
            "Adjust the max concurrent downloads in Settings to optimize bandwidth usage.",
            "Thumbnail cache is managed automatically — oldest thumbnails are evicted first (LRU).",
            "Export your download history to CSV for record-keeping.",
            "Failed downloads in Bulk mode are automatically retried based on your retry settings.",
        ]

        for tip in tips:
            tip_label = QLabel(f"  •  {tip}")
            tip_label.setStyleSheet("color: #b3b3b3; font-size: 13px; border: none;")
            tip_label.setWordWrap(True)
            tips_layout.addWidget(tip_label)

        layout.addWidget(tips_frame)

        # ── Footer ──────────────────────────────────────────────────────
        footer_frame = QFrame()
        footer_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)
        footer_layout = QVBoxLayout(footer_frame)
        footer_layout.setContentsMargins(0, 10, 0, 10)

        disclaimer = QLabel(
            "Disclaimer: This tool is intended for personal use only. "
            "Respect content creators' rights and TikTok's terms of service."
        )
        disclaimer.setStyleSheet("color: #666; font-size: 11px; font-style: italic; border: none;")
        disclaimer.setAlignment(Qt.AlignCenter)
        disclaimer.setWordWrap(True)
        footer_layout.addWidget(disclaimer)

        copyright_label = QLabel("© 2026 TikTok Video Downloader. All rights reserved.")
        copyright_label.setStyleSheet("color: #555; font-size: 11px; border: none;")
        copyright_label.setAlignment(Qt.AlignCenter)
        footer_layout.addWidget(copyright_label)

        layout.addWidget(footer_frame)
        layout.addStretch()

        scroll.setWidget(container)

        # Set scroll as main widget
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _create_feature_card(self, icon, title, description):
        """Creates a polished feature card with icon, title, and description."""
        card = GlowingFrame()
        card.setStyleSheet("""
            GlowingFrame {
                background-color: #1a1a1a;
                border-radius: 12px;
                border: 1px solid #2c2c2c;
            }
            GlowingFrame:hover {
                background-color: #222222;
            }
        """)
        card.setMinimumHeight(140)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(8)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 28px; border: none; background: transparent;")
        card_layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #00f2fe; border: none; background: transparent;")
        card_layout.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setStyleSheet("font-size: 12px; color: #999; border: none; background: transparent;")
        desc_label.setWordWrap(True)
        card_layout.addWidget(desc_label)

        card_layout.addStretch()
        return card

    def _create_tech_chip(self, name, detail):
        """Creates a small tech stack chip/badge."""
        chip = QFrame()
        chip.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border-radius: 8px;
                border: 1px solid #333;
            }
            QFrame:hover {
                border-color: #00f2fe;
            }
        """)
        chip_layout = QVBoxLayout(chip)
        chip_layout.setContentsMargins(12, 8, 12, 8)
        chip_layout.setSpacing(2)

        name_label = QLabel(name)
        name_label.setStyleSheet("font-size: 13px; font-weight: bold; color: white; border: none;")
        name_label.setAlignment(Qt.AlignCenter)
        chip_layout.addWidget(name_label)

        detail_label = QLabel(detail)
        detail_label.setStyleSheet("font-size: 10px; color: #888; border: none;")
        detail_label.setAlignment(Qt.AlignCenter)
        chip_layout.addWidget(detail_label)

        return chip
