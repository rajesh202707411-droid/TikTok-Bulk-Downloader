from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QStackedWidget, QLabel, QSpacerItem, QSizePolicy, QFrame, QApplication, QMessageBox
)
import re
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon

# Import screens (to be created)
from ui.screens.home import HomeScreen
from ui.screens.single_download import SingleDownloadScreen
from ui.screens.profile_download import ProfileDownloadScreen
from ui.screens.bulk_download import BulkDownloadScreen
from ui.screens.history import HistoryScreen
from ui.screens.settings import SettingsScreen
from ui.screens.about import AboutScreen

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TikTok Video Downloader")
        self.setMinimumSize(1000, 700)
        
        self.setup_ui()

    def setup_ui(self):
        # Central Widget and Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setStyleSheet("background-color: #121212; border-right: 1px solid #2c2c2c;")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)
        sidebar_layout.setSpacing(10)

        # App Title in Sidebar
        title_label = QLabel("TikDownloader")
        font = QFont("Arial", 16, QFont.Bold)
        title_label.setFont(font)
        title_label.setStyleSheet("color: white; border: none; padding-bottom: 20px;")
        title_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(title_label)

        # Stacked Widget for Screens
        self.stacked_widget = QStackedWidget()
        
        # Initialize Screens
        self.screens = {
            "Home": HomeScreen(),
            "Single Download": SingleDownloadScreen(),
            "Profile Download": ProfileDownloadScreen(),
            "Bulk Download": BulkDownloadScreen(),
            "History": HistoryScreen(),
            "Settings": SettingsScreen(),
            "About": AboutScreen()
        }

        # Navigation Buttons
        self.nav_buttons = {}
        for name, screen in self.screens.items():
            self.stacked_widget.addWidget(screen)
            btn = QPushButton(name)
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 10px 15px;
                    border: none;
                    background: transparent;
                    color: #b3b3b3;
                    font-size: 14px;
                }
                QPushButton:hover {
                    color: white;
                    background-color: #2c2c2c;
                    border-radius: 5px;
                }
                QPushButton:checked {
                    color: white;
                    background-color: #333333;
                    border-left: 3px solid #00f2fe;
                    border-radius: 5px;
                }
            """)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, n=name: self.switch_screen(n))
            self.nav_buttons[name] = btn
            
            # Group specific sections (e.g., push Settings/About to bottom)
            if name == "Settings":
                spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
                sidebar_layout.addItem(spacer)
            
            sidebar_layout.addWidget(btn)

        # Connect cross-screen signals
        self.screens["Profile Download"].send_to_bulk.connect(self.on_send_to_bulk)

        # Setup Clipboard monitoring
        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self.on_clipboard_changed)

        # Add Sidebar and Stacked Widget to Main Layout
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stacked_widget)

        # Set default screen
        self.switch_screen("Home")

    def on_clipboard_changed(self):
        text = self.clipboard.text()
        if text and "tiktok.com" in text:
            # Check if it's a profile or a single video
            if "/video/" in text or "vm.tiktok.com" in text or "vt.tiktok.com" in text:
                reply = QMessageBox.question(self, "TikTok URL Detected", 
                                             "A TikTok video URL was copied to your clipboard. Do you want to download it?",
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                if reply == QMessageBox.Yes:
                    self.switch_screen("Single Download")
                    self.screens["Single Download"].url_input.setText(text)
            elif "@" in text and "/video/" not in text:
                reply = QMessageBox.question(self, "TikTok Profile Detected", 
                                             "A TikTok profile URL was copied to your clipboard. Do you want to extract it?",
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                if reply == QMessageBox.Yes:
                    self.switch_screen("Profile Download")
                    self.screens["Profile Download"].url_input.setText(text)

    def on_send_to_bulk(self, urls):
        self.switch_screen("Bulk Download")
        self.screens["Bulk Download"].add_urls(urls)

    def switch_screen(self, screen_name):
        # Update button states
        for name, btn in self.nav_buttons.items():
            btn.setChecked(name == screen_name)
        
        # Switch widget
        screen_widget = self.screens[screen_name]
        self.stacked_widget.setCurrentWidget(screen_widget)
