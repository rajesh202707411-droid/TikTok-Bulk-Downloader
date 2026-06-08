from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QSpinBox, QFileDialog, QMessageBox, QFormLayout, QCheckBox
)
from settings.config import config_mgr
from downloader.thumbnail_manager import thumbnail_mgr

class SettingsScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.config = config_mgr.load()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Title
        title = QLabel("Settings")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        layout.addWidget(title)

        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        # Download Directory
        dir_layout = QHBoxLayout()
        self.dir_input = QLineEdit(self.config.get("download_dir", "downloads"))
        self.dir_input.setReadOnly(True)
        self.dir_input.setStyleSheet("padding: 5px;")
        
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setStyleSheet("padding: 5px 15px;")
        self.browse_btn.clicked.connect(self.browse_dir)
        
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(self.browse_btn)
        
        form_layout.addRow(self.create_label("Download Folder:"), dir_layout)

        # Max Concurrent Downloads
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 10)
        self.concurrent_spin.setValue(self.config.get("max_concurrent", 2))
        self.concurrent_spin.setStyleSheet("padding: 5px; color: white; background-color: #2c2c2c;")
        form_layout.addRow(self.create_label("Max Concurrent Downloads:"), self.concurrent_spin)

        # Auto Retry
        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(0, 10)
        self.retry_spin.setValue(self.config.get("auto_retry", 3))
        self.retry_spin.setStyleSheet("padding: 5px; color: white; background-color: #2c2c2c;")
        form_layout.addRow(self.create_label("Auto Retry Count:"), self.retry_spin)
        
        # Thumbnail Cache
        self.cache_enable_cb = QCheckBox("Enable Thumbnail Cache")
        self.cache_enable_cb.setChecked(self.config.get("enable_thumbnail_cache", True))
        self.cache_enable_cb.setStyleSheet("color: white;")
        form_layout.addRow(self.create_label("Thumbnail Cache:"), self.cache_enable_cb)

        self.cache_limit_spin = QSpinBox()
        self.cache_limit_spin.setRange(10, 2000)
        self.cache_limit_spin.setSuffix(" MB")
        self.cache_limit_spin.setValue(self.config.get("thumbnail_cache_limit_mb", 100))
        self.cache_limit_spin.setStyleSheet("padding: 5px; color: white; background-color: #2c2c2c;")
        form_layout.addRow(self.create_label("Cache Size Limit:"), self.cache_limit_spin)

        # Clear Cache Button
        self.clear_cache_btn = QPushButton("Clear Thumbnail Cache")
        self.clear_cache_btn.setStyleSheet("padding: 5px; background-color: #2c2c2c; color: white;")
        self.clear_cache_btn.clicked.connect(self.clear_cache)
        form_layout.addRow(self.create_label("Maintenance:"), self.clear_cache_btn)

        layout.addLayout(form_layout)

        # Save Button
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setStyleSheet("""
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
        self.save_btn.clicked.connect(self.save_settings)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        
        layout.addLayout(btn_layout)
        layout.addStretch()

    def create_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size: 14px; color: #b3b3b3;")
        return lbl

    def browse_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Download Directory")
        if directory:
            self.dir_input.setText(directory)

    def clear_cache(self):
        if thumbnail_mgr.clear_all():
            QMessageBox.information(self, "Success", "Thumbnail cache cleared successfully!")
        else:
            QMessageBox.critical(self, "Error", "Failed to clear thumbnail cache.")

    def save_settings(self):
        self.config["download_dir"] = self.dir_input.text()
        self.config["max_concurrent"] = self.concurrent_spin.value()
        self.config["auto_retry"] = self.retry_spin.value()
        self.config["enable_thumbnail_cache"] = self.cache_enable_cb.isChecked()
        self.config["thumbnail_cache_limit_mb"] = self.cache_limit_spin.value()
        
        config_mgr.save(self.config)
        QMessageBox.information(self, "Success", "Settings saved successfully!")
