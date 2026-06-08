from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QMessageBox,
    QDialog, QApplication, QAbstractItemView
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QRect
from PySide6.QtGui import QIcon, QPixmap, QImage, QPainter, QPainterPath
from workers.download_worker import DownloadWorker, InfoExtractorWorker, ThumbnailLoaderWorker
from database.db_manager import DBManager
from settings.config import config_mgr
from utils import extract_date_from_info

class QueueProcessingWorker(QThread):
    batch_ready = Signal(list)
    progress_update = Signal(int, int)
    finished_processing = Signal(float)

    def __init__(self, urls, existing_urls, batch_size=100):
        super().__init__()
        self.urls = urls
        self.existing_urls = set(existing_urls)
        self.batch_size = batch_size
        self.is_cancelled = False
        import time
        self.start_time = time.time()

    def run(self):
        batch = []
        total = len(self.urls)
        processed = 0

        for url in self.urls:
            if self.is_cancelled:
                break
                
            if url in self.existing_urls:
                processed += 1
                self.progress_update.emit(processed, total)
                continue
                
            batch.append(url)
            self.existing_urls.add(url)
            processed += 1
            
            if len(batch) >= self.batch_size:
                self.batch_ready.emit(batch)
                batch = []
                self.progress_update.emit(processed, total)
                self.msleep(100) # give UI time to update
                
        if batch and not self.is_cancelled:
            self.batch_ready.emit(batch)
            self.progress_update.emit(processed, total)
            
        import time
        elapsed = time.time() - self.start_time
        self.finished_processing.emit(elapsed)

    def cancel(self):
        self.is_cancelled = True

class ProcessingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Processing Videos")
        self.setFixedSize(350, 150)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)
        
        layout = QVBoxLayout(self)
        
        self.msg_label = QLabel("Please wait while videos are being added to the download queue.")
        self.msg_label.setWordWrap(True)
        layout.addWidget(self.msg_label)
        
        self.progress_label = QLabel("Adding videos to queue...\n0 / 0")
        self.progress_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        self.cancel_btn = QPushButton("Cancel")
        layout.addWidget(self.cancel_btn, alignment=Qt.AlignCenter)
        
    def update_progress(self, processed, total):
        self.progress_label.setText(f"Adding videos to queue...\n{processed} / {total}")
        if total > 0:
            self.progress_bar.setValue(int((processed / total) * 100))


class QueueClearWorker(QThread):
    """Background worker for clearing queue items from the database without freezing the UI."""
    finished = Signal(int)
    error = Signal(str)

    def __init__(self, db_manager, urls=None, clear_all=False):
        super().__init__()
        self.db = db_manager
        self.urls = urls or []
        self.clear_all = clear_all

    def run(self):
        try:
            if self.clear_all:
                self.db.clear_queue_by_status([])
                self.finished.emit(len(self.urls))
            elif self.urls:
                chunk_size = 500
                for i in range(0, len(self.urls), chunk_size):
                    chunk = self.urls[i:i + chunk_size]
                    self.db.remove_from_queue_bulk(chunk)
                self.finished.emit(len(self.urls))
            else:
                self.finished.emit(0)
        except Exception as e:
            from logger import logger
            logger.error(f"QueueClearWorker failed: {e}")
            self.error.emit(str(e))


class BulkDownloadScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.queue = [] 
        # item: {'url': str, 'status': str, 'worker': obj, 'filename': str, 'title': str, 'thumb_url': str, 'thumb_path': str}
        config = config_mgr.load()
        self.max_concurrent = config.get("max_concurrent", 2)
        self.active_downloads = 0
        self.is_paused = False
        self.db = DBManager()
        self.setup_ui()
        
        self.queue_timer = QTimer(self)
        self.queue_timer.timeout.connect(self.process_queue)
        self.queue_timer.start(1000)
        
        self.info_workers = {}
        self.thumb_workers = {}

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title = QLabel("Bulk Download")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        layout.addWidget(title)

        self.url_input = QTextEdit()
        self.url_input.setPlaceholderText("Paste multiple TikTok URLs here (one per line)...")
        self.url_input.setMaximumHeight(100)
        layout.addWidget(self.url_input)
        
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add to Queue")
        self.add_btn.setStyleSheet("padding: 8px;")
        self.add_btn.clicked.connect(self.add_urls)
        
        self.start_btn = QPushButton("Start/Resume Queue")
        self.start_btn.setStyleSheet("padding: 8px; background-color: #00f2fe; color: black;")
        self.start_btn.clicked.connect(self.resume_queue)
        
        self.pause_btn = QPushButton("Pause Queue")
        self.pause_btn.setStyleSheet("padding: 8px;")
        self.pause_btn.clicked.connect(self.pause_queue)
        
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.pause_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Queue management buttons (Remove Selected / Completed / Failed / All)
        mgmt_layout = QHBoxLayout()

        self.remove_selected_btn = QPushButton("Remove Selected")
        self.remove_selected_btn.setStyleSheet("padding: 8px; background-color: #2c2c2c; color: white;")
        self.remove_selected_btn.clicked.connect(self.remove_selected)

        self.remove_completed_btn = QPushButton("Remove Completed")
        self.remove_completed_btn.setStyleSheet("padding: 8px; background-color: #2c2c2c; color: white;")
        self.remove_completed_btn.clicked.connect(self.remove_completed)

        self.remove_failed_btn = QPushButton("Remove Failed")
        self.remove_failed_btn.setStyleSheet("padding: 8px; background-color: #2c2c2c; color: white;")
        self.remove_failed_btn.clicked.connect(self.remove_failed)

        self.remove_all_btn = QPushButton("Remove All")
        self.remove_all_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #fe0979;
                color: white;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d10763;
            }
            QPushButton:disabled {
                background-color: #444;
                color: #888;
            }
        """)
        self.remove_all_btn.clicked.connect(self.remove_all)

        mgmt_layout.addWidget(self.remove_selected_btn)
        mgmt_layout.addWidget(self.remove_completed_btn)
        mgmt_layout.addWidget(self.remove_failed_btn)
        mgmt_layout.addStretch()
        mgmt_layout.addWidget(self.remove_all_btn)
        layout.addLayout(mgmt_layout)

        # Initially hide management buttons
        self._set_mgmt_visible(False)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Thumb", "Title", "Status", "Progress", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(3, 150)
        self.table.setColumnWidth(4, 80)

        # Enable multi-row selection for "Remove Selected"
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # Make rows taller for thumbnails
        self.table.verticalHeader().setDefaultSectionSize(100)
        
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #121212;
                color: white;
                border: 1px solid #2c2c2c;
            }
        """)
        self.table.verticalScrollBar().valueChanged.connect(self.load_visible_thumbnails)
        self.table.itemSelectionChanged.connect(self.update_mgmt_buttons)
        layout.addWidget(self.table)

    def add_urls(self, urls=None):
        if not urls:
            text = self.url_input.toPlainText()
            urls = [line.strip() for line in text.split('\n') if line.strip()]
            self.url_input.clear()
            
        if not urls:
            return
            
        existing_urls = [item['url'] for item in self.queue]
        self.added_count = 0
        
        self.processing_dialog = ProcessingDialog(self)
        self.processing_worker = QueueProcessingWorker(urls, existing_urls, batch_size=100)
        
        self.processing_dialog.cancel_btn.clicked.connect(self.cancel_processing)
        self.processing_worker.progress_update.connect(self.processing_dialog.update_progress)
        self.processing_worker.batch_ready.connect(self.on_batch_ready)
        self.processing_worker.finished_processing.connect(self.on_processing_finished)
        
        self.processing_dialog.show()
        self.processing_worker.start()

    def cancel_processing(self):
        self.processing_worker.cancel()
        self.processing_dialog.accept()

    def on_batch_ready(self, batch):
        self.table.setUpdatesEnabled(False)
        for url in batch:
            item = {'url': url, 'status': 'Queued', 'worker': None, 'progress': 0, 'title': url, 'thumb_path': None}
            self.queue.append(item)
            index = len(self.queue) - 1
            
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            thumb_label = QLabel("Loading...")
            thumb_label.setAlignment(Qt.AlignCenter)
            self.table.setCellWidget(row, 0, thumb_label)
            
            self.table.setItem(row, 1, QTableWidgetItem(url))
            self.table.setItem(row, 2, QTableWidgetItem("Queued"))
            
            pb = QProgressBar()
            pb.setRange(0, 100)
            pb.setValue(0)
            self.table.setCellWidget(row, 3, pb)
            
            cancel_btn = QPushButton("Remove")
            cancel_btn.clicked.connect(lambda checked, u=url: self.remove_item(u))
            self.table.setCellWidget(row, 4, cancel_btn)
            
            self.added_count += 1
        
        self.table.setUpdatesEnabled(True)
        QTimer.singleShot(100, self.load_visible_thumbnails)
        self.update_mgmt_buttons()

    def on_processing_finished(self, elapsed):
        self.processing_dialog.accept()
        QMessageBox.information(self, "Videos Added Successfully", f"{self.added_count} videos added to Bulk Download Queue.\n\nTime Taken: {elapsed:.1f} seconds")
        self.added_count = 0

    def load_visible_thumbnails(self):
        viewport = self.table.viewport()
        rect = viewport.rect()
        
        for row in range(self.table.rowCount()):
            item_rect = self.table.visualRect(self.table.model().index(row, 0))
            if item_rect.intersects(rect):
                self.fetch_metadata(row)

    def fetch_metadata(self, index):
        if index in self.info_workers:
            return
            
        item = self.queue[index]
        worker = InfoExtractorWorker(item['url'])
        worker.finished.connect(lambda info, idx=index: self.on_info_finished(idx, info))
        self.info_workers[index] = worker
        worker.start()

    def on_info_finished(self, index, info):
        if index >= len(self.queue):
            return
        item = self.queue[index]
        
        if info:
            item['title'] = info.get('title', item['url'])
            self.table.item(index, 1).setText(item['title'])
            item['upload_date'] = extract_date_from_info(info)
            
            thumb_url = info.get('thumbnail')
            if thumb_url:
                vid_id = info.get('id', str(index))
                t_worker = ThumbnailLoaderWorker(thumb_url, vid_id)
                t_worker.finished.connect(lambda data, id_, idx=index: self.on_thumbnail_loaded(idx, data, id_))
                self.thumb_workers[index] = t_worker
                t_worker.start()

    def on_thumbnail_loaded(self, index, data, identifier):
        if index >= len(self.queue):
            return
        
        # Also store the path for DB
        from downloader.thumbnail_manager import thumbnail_mgr
        self.queue[index]['thumb_path'] = thumbnail_mgr.get_cache_path(identifier)
        
        image = QImage()
        image.loadFromData(data)
        pixmap = QPixmap(image).scaled(90, 90, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        
        # Rounded
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
        
        label = QLabel()
        label.setPixmap(rounded)
        label.setAlignment(Qt.AlignCenter)
        self.table.setCellWidget(index, 0, label)

    def remove_item(self, url):
        for i, item in enumerate(self.queue):
            if item['url'] == url:
                if item['status'] == 'Downloading':
                    QMessageBox.warning(self, "Warning", "Cannot remove an active download.")
                    return
                self.queue.pop(i)
                self.table.removeRow(i)
                break

    def pause_queue(self):
        self.is_paused = True
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.update_mgmt_buttons()

    def resume_queue(self):
        self.is_paused = False
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.update_mgmt_buttons()
        self.process_queue()

    def process_queue(self):
        if self.is_paused:
            return
        self.active_downloads = sum(1 for item in self.queue if item['status'] == 'Downloading')
        
        for i, item in enumerate(self.queue):
            if self.active_downloads >= self.max_concurrent:
                break
            if item['status'] in ['Queued', 'Failed']:
                self.start_download(i)
                self.active_downloads += 1

    def start_download(self, index):
        item = self.queue[index]
        item['status'] = 'Downloading'
        self.table.item(index, 2).setText('Downloading')
        
        worker = DownloadWorker(item['url'], 'best')
        worker.progress.connect(lambda data, idx=index: self.on_progress(idx, data))
        worker.finished.connect(lambda success, idx=index: self.on_finished(idx, success))
        worker.error.connect(lambda msg, idx=index: self.on_error(idx, msg))
        
        item['worker'] = worker
        worker.start()

    def on_progress(self, index, data):
        if index >= len(self.queue):
            return
        if data['status'] == 'downloading':
            pb = self.table.cellWidget(index, 3)
            if pb:
                pb.setValue(int(data['percent']))
        elif data['status'] == 'finished':
            self.queue[index]['filename'] = data.get('filename', '')

    def on_finished(self, index, success):
        if index >= len(self.queue):
            return
        item = self.queue[index]
        item['status'] = 'Completed' if success else 'Failed'
        self.table.item(index, 2).setText(item['status'])
        pb = self.table.cellWidget(index, 3)
        if pb and success:
            pb.setValue(100)
            
        self.db.add_download(
            url=item['url'], 
            title=item.get('title', 'Bulk Download'), 
            file_path=item.get('filename', ''), 
            status=item['status'],
            thumbnail_path=item.get('thumb_path', ''),
            cache_status='cached' if item.get('thumb_path') else 'none',
            upload_date=item.get('upload_date')
        )
        
        self.active_downloads -= 1
        self.update_mgmt_buttons()
        self.process_queue()

    def on_error(self, index, msg):
        if index >= len(self.queue):
            return
        item = self.queue[index]
        item['status'] = 'Failed'
        self.table.item(index, 2).setText('Failed')
        
        self.db.add_download(
            url=item['url'], 
            title=item.get('title', 'Bulk Download'), 
            file_path="", 
            status="Failed",
            upload_date=item.get('upload_date')
        )
        
        self.active_downloads -= 1
        self.update_mgmt_buttons()
        self.process_queue()

    # ── Queue Management Methods ────────────────────────────────────────

    def update_mgmt_buttons(self):
        """Update management button visibility and enabled state based on queue state."""
        has_items = len(self.queue) > 0
        self._set_mgmt_visible(has_items)

        if has_items:
            has_completed = any(item['status'] == 'Completed' for item in self.queue)
            has_failed = any(item['status'] == 'Failed' for item in self.queue)
            has_selection = (
                len(self.table.selectionModel().selectedRows()) > 0
                if self.table.selectionModel() else False
            )

            self.remove_completed_btn.setEnabled(has_completed)
            self.remove_failed_btn.setEnabled(has_failed)
            self.remove_selected_btn.setEnabled(has_selection)
            # "Remove All" is only enabled when the queue is paused
            self.remove_all_btn.setEnabled(self.is_paused)

    def _set_mgmt_visible(self, visible):
        """Show or hide all queue management buttons."""
        self.remove_selected_btn.setVisible(visible)
        self.remove_completed_btn.setVisible(visible)
        self.remove_failed_btn.setVisible(visible)
        self.remove_all_btn.setVisible(visible)

    def remove_all(self):
        """Remove all downloads from the queue with confirmation dialog."""
        if not self.queue:
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Remove All Downloads")
        msg.setText(
            "This will remove all downloads from the queue and download list.\n\n"
            "Downloaded files on disk will NOT be deleted.\n\n"
            "Do you want to continue?"
        )
        msg.setIcon(QMessageBox.Warning)
        remove_btn = msg.addButton("Remove All", QMessageBox.AcceptRole)
        msg.addButton("Cancel", QMessageBox.RejectRole)
        msg.exec()

        if msg.clickedButton() == remove_btn:
            self._removal_label = "all"
            self._perform_bulk_removal(list(range(len(self.queue))))

    def remove_selected(self):
        """Remove table-selected rows from the queue."""
        selected_rows = sorted(
            set(index.row() for index in self.table.selectionModel().selectedRows())
        )
        if not selected_rows:
            QMessageBox.information(self, "No Selection", "Please select rows to remove.")
            return

        # Block removal of actively downloading items unless queue is paused
        active_in_sel = [
            i for i in selected_rows
            if i < len(self.queue) and self.queue[i]['status'] == 'Downloading'
        ]
        if active_in_sel and not self.is_paused:
            QMessageBox.warning(
                self, "Active Downloads",
                "Some selected items are currently downloading.\n"
                "Pause the queue first to remove them."
            )
            return

        self._removal_label = "selected"
        self._perform_bulk_removal(selected_rows)

    def remove_completed(self):
        """Remove all completed downloads from the queue."""
        indices = [i for i, item in enumerate(self.queue) if item['status'] == 'Completed']
        if not indices:
            QMessageBox.information(self, "Nothing to Remove", "No completed downloads to remove.")
            return
        self._removal_label = "completed"
        self._perform_bulk_removal(indices)

    def remove_failed(self):
        """Remove all failed downloads from the queue."""
        indices = [i for i, item in enumerate(self.queue) if item['status'] == 'Failed']
        if not indices:
            QMessageBox.information(self, "Nothing to Remove", "No failed downloads to remove.")
            return
        self._removal_label = "failed"
        self._perform_bulk_removal(indices)

    def _perform_bulk_removal(self, indices_to_remove):
        """Remove items at given indices from the queue, table, and database.

        Uses a background worker for database operations to avoid UI freezes
        on large queues (500-5000+ items).
        """
        if not indices_to_remove:
            return

        indices_set = set(indices_to_remove)
        remove_all = len(indices_to_remove) == len(self.queue)

        # Collect URLs before modifying the queue
        urls_to_remove = [
            self.queue[i]['url'] for i in indices_to_remove if i < len(self.queue)
        ]

        if remove_all:
            # ── Fast path: clear everything at once ──
            # Cancel all active download workers
            for item in self.queue:
                worker = item.get('worker')
                if worker and worker.isRunning():
                    worker.terminate()
                    worker.wait(2000)

            # Cancel all info / thumbnail workers
            for w in self.info_workers.values():
                if w.isRunning():
                    w.terminate()
            for w in self.thumb_workers.values():
                if w.isRunning():
                    w.terminate()

            self.queue.clear()
            self.table.setRowCount(0)
            self.active_downloads = 0
            self.info_workers.clear()
            self.thumb_workers.clear()
        else:
            # ── Selective removal ──
            # Cancel workers for removed indices
            for i in indices_to_remove:
                if i < len(self.queue):
                    worker = self.queue[i].get('worker')
                    if worker and worker.isRunning():
                        worker.terminate()
                        worker.wait(2000)

                if i in self.info_workers:
                    w = self.info_workers.pop(i)
                    if w.isRunning():
                        w.terminate()
                if i in self.thumb_workers:
                    w = self.thumb_workers.pop(i)
                    if w.isRunning():
                        w.terminate()

            # Remove from queue (reverse order to preserve indices)
            for i in sorted(indices_to_remove, reverse=True):
                if i < len(self.queue):
                    self.queue.pop(i)

            # Remove from table (single batch UI update)
            self.table.setUpdatesEnabled(False)
            for i in sorted(indices_to_remove, reverse=True):
                if i < self.table.rowCount():
                    self.table.removeRow(i)
            self.table.setUpdatesEnabled(True)

            # Recount active downloads
            self.active_downloads = sum(
                1 for item in self.queue if item['status'] == 'Downloading'
            )

            # Remap worker indices after removal
            sorted_removed = sorted(indices_to_remove)
            new_info = {}
            for old_i, w in list(self.info_workers.items()):
                if old_i in indices_set:
                    continue
                new_i = old_i - sum(1 for r in sorted_removed if r < old_i)
                if 0 <= new_i < len(self.queue):
                    new_info[new_i] = w
            new_thumb = {}
            for old_i, w in list(self.thumb_workers.items()):
                if old_i in indices_set:
                    continue
                new_i = old_i - sum(1 for r in sorted_removed if r < old_i)
                if 0 <= new_i < len(self.queue):
                    new_thumb[new_i] = w
            self.info_workers = new_info
            self.thumb_workers = new_thumb

        # Background database cleanup
        self.clear_worker = QueueClearWorker(
            self.db, urls=urls_to_remove, clear_all=remove_all
        )
        self.clear_worker.finished.connect(self._on_clear_finished)
        self.clear_worker.error.connect(self._on_clear_error)
        self.clear_worker.start()

    def _on_clear_finished(self, count):
        """Handle successful queue clear from background worker."""
        self.update_mgmt_buttons()
        label = getattr(self, '_removal_label', 'all')
        if label == "all":
            message = "All downloads removed from queue.\n\nQueue cleared successfully."
        else:
            message = f"All {label} downloads removed from queue.\n\nQueue cleared successfully."
        QMessageBox.information(self, "Queue Cleared", message)

    def _on_clear_error(self, error_msg):
        """Handle queue clear failure."""
        self.update_mgmt_buttons()
        QMessageBox.critical(self, "Error", f"Failed to update queue database:\n{error_msg}")
