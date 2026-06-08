import psutil
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt, QTimer
from database.db_manager import DBManager

class HomeScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DBManager()
        self.setup_ui()
        
        # Timer for performance monitoring
        self.perf_timer = QTimer(self)
        self.perf_timer.timeout.connect(self.update_performance)
        self.perf_timer.start(1000)
        
        # Initial stats update
        self.update_stats()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Welcome
        title = QLabel("Welcome to TikTok Video Downloader")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: white;")
        layout.addWidget(title, alignment=Qt.AlignTop)

        # Stats Cards Layout
        stats_layout = QHBoxLayout()
        
        # Total Downloads Card
        self.total_downloads_label = self.create_card(stats_layout, "Total Downloads", "0")
        
        # Successful Downloads Card
        self.success_downloads_label = self.create_card(stats_layout, "Successful", "0", color="#00f2fe")
        
        layout.addLayout(stats_layout)

        # Performance Monitoring
        perf_label = QLabel("System Performance")
        perf_label.setStyleSheet("font-size: 20px; font-weight: bold; color: white; margin-top: 20px;")
        layout.addWidget(perf_label)

        perf_layout = QHBoxLayout()
        self.cpu_label = self.create_card(perf_layout, "CPU Usage", "0%", color="#fe0979")
        self.ram_label = self.create_card(perf_layout, "RAM Usage", "0 MB", color="#fe0979")
        layout.addLayout(perf_layout)
        
        layout.addStretch()

    def create_card(self, parent_layout, title, value, color="white"):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border-radius: 10px;
                border: 1px solid #2c2c2c;
            }
        """)
        card_layout = QVBoxLayout(card)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 14px; color: #b3b3b3; border: none;")
        
        value_label = QLabel(value)
        value_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {color}; border: none;")
        
        card_layout.addWidget(title_label)
        card_layout.addWidget(value_label)
        
        parent_layout.addWidget(card)
        return value_label

    def update_stats(self):
        history = self.db.get_all_downloads()
        total = len(history)
        success = sum(1 for h in history if h.status == 'Completed')
        
        self.total_downloads_label.setText(str(total))
        self.success_downloads_label.setText(str(success))

    def update_performance(self):
        try:
            # CPU Usage
            cpu = psutil.cpu_percent()
            self.cpu_label.setText(f"{cpu:.1f}%")
            
            # RAM Usage (of this specific process)
            process = psutil.Process()
            mem_info = process.memory_info()
            ram_mb = mem_info.rss / (1024 * 1024)
            self.ram_label.setText(f"{ram_mb:.1f} MB")
        except Exception:
            pass
            
    def showEvent(self, event):
        super().showEvent(event)
        self.update_stats()
