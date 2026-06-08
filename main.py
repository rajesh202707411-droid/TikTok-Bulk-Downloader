import sys
import os
import qdarktheme
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from logger import logger

def setup_environment():
    # Create necessary directories if they don't exist
    directories = ['logs', 'cache', 'downloads', 'database']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def main():
    logger.info("Application starting...")
    setup_environment()
    
    app = QApplication(sys.argv)
    
    # Apply TikTok-inspired dark theme
    # Primary: Black/Dark Gray, Accent: TikTok Cyan (#00f2fe) / Pink (#fe0979)
    qdarktheme.setup_theme(
        theme="dark",
        custom_colors={
            "[dark]": {
                "primary": "#00f2fe", # TikTok Cyan
                "background": "#121212", # Dark background
                "border": "#2c2c2c",
            }
        }
    )
    
    # Optional: Apply custom stylesheet overrides for specific TikTok feel
    app.setStyleSheet(app.styleSheet() + """
        QMainWindow {
            background-color: #000000;
        }
        QPushButton {
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #fe0979; /* TikTok Pink on hover for accents */
            color: white;
        }
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
