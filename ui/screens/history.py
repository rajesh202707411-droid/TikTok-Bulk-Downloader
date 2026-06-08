import csv
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage, QPainter, QPainterPath
from database.db_manager import DBManager

class HistoryScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DBManager()
        self.setup_ui()
        self.load_history()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Download History")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        layout.addWidget(title)

        top_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by title or URL...")
        self.search_input.setStyleSheet("padding: 8px;")
        self.search_input.textChanged.connect(self.load_history)
        
        self.export_btn = QPushButton("Export CSV")
        self.export_btn.setStyleSheet("padding: 8px 15px; background-color: #2c2c2c;")
        self.export_btn.clicked.connect(self.export_csv)
        
        self.clear_btn = QPushButton("Clear History")
        self.clear_btn.setStyleSheet("padding: 8px 15px; background-color: #fe0979; color: white;")
        self.clear_btn.clicked.connect(self.clear_history)
        
        top_layout.addWidget(self.search_input)
        top_layout.addWidget(self.export_btn)
        top_layout.addWidget(self.clear_btn)
        layout.addLayout(top_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Thumb", "Title", "URL", "Uploaded", "Downloaded", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(2, 150)
        self.table.setColumnWidth(3, 110)
        self.table.setColumnWidth(4, 150)
        self.table.setColumnWidth(5, 100)
        
        self.table.verticalHeader().setDefaultSectionSize(100)
        
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #121212;
                color: white;
                border: 1px solid #2c2c2c;
            }
        """)
        layout.addWidget(self.table)

    def load_history(self):
        search_query = self.search_input.text().strip()
        history = self.db.get_all_downloads(search_query)
        
        self.table.setRowCount(len(history))
        for row, item in enumerate(history):
            # Thumbnail
            thumb_label = QLabel()
            thumb_label.setAlignment(Qt.AlignCenter)
            
            # Load local image if path exists
            if item.thumbnail_path and os.path.exists(item.thumbnail_path):
                pixmap = QPixmap(item.thumbnail_path).scaled(90, 90, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                rounded = QPixmap(90, 90)
                rounded.fill(Qt.transparent)
                painter = QPainter(rounded)
                painter.setRenderHint(QPainter.Antialiasing)
                path = QPainterPath()
                path.addRoundedRect(0, 0, 90, 90, 5, 5)
                painter.setClipPath(path)
                x = (90 - pixmap.width()) // 2
                y = (90 - pixmap.height()) // 2
                painter.drawPixmap(x, y, pixmap)
                painter.end()
                thumb_label.setPixmap(rounded)
            else:
                thumb_label.setText("No Image")
                
            self.table.setCellWidget(row, 0, thumb_label)
            
            self.table.setItem(row, 1, QTableWidgetItem(item.title))
            self.table.setItem(row, 2, QTableWidgetItem(item.url))
            self.table.setItem(row, 3, QTableWidgetItem(item.upload_date if item.upload_date else "Unknown"))
            self.table.setItem(row, 4, QTableWidgetItem(item.download_date.strftime("%Y-%m-%d %H:%M")))
            self.table.setItem(row, 5, QTableWidgetItem(item.status))

    def export_csv(self):
        history = self.db.get_all_downloads(self.search_input.text().strip())
        if not history:
            QMessageBox.warning(self, "Warning", "No history to export.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "", "CSV Files (*.csv)")
        if file_path:
            try:
                import csv
                with open(file_path, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(["ID", "Title", "URL", "File Path", "Uploaded", "Downloaded", "Status"])
                    for item in history:
                        writer.writerow([item.id, item.title, item.url, item.file_path, item.upload_date, item.download_date, item.status])
                QMessageBox.information(self, "Success", "History exported successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export CSV: {e}")

    def clear_history(self):
        reply = QMessageBox.question(self, "Confirm", "Are you sure you want to clear all history?", 
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.db.clear_history():
                self.load_history()
                QMessageBox.information(self, "Success", "History cleared.")
            else:
                QMessageBox.critical(self, "Error", "Failed to clear history.")
