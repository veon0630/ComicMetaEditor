"""
Update notification dialog for displaying available updates.
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTextEdit, QWidget, QProgressBar)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import webbrowser

from core.translator import translator


class UpdateDialog(QDialog):
    """Dialog to show update information and provide download link."""
    
    def __init__(self, current_version, latest_version, release_notes, download_url, is_zip=False, parent=None):
        super().__init__(parent)
        self.download_url = download_url
        self.is_zip = is_zip
        self.downloaded_file = None
        self.init_ui(current_version, latest_version, release_notes)
        
    def init_ui(self, current_version, latest_version, release_notes):
        self.setWindowTitle(translator.tr("Update Available"))
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel(translator.tr("A new version is available!"))
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Version info
        version_widget = QWidget()
        version_layout = QHBoxLayout(version_widget)
        version_layout.setContentsMargins(0, 10, 0, 10)
        
        current_label = QLabel(translator.tr("Current version: {}").format(current_version))
        latest_label = QLabel(translator.tr("Latest version: {}").format(latest_version))
        latest_label.setStyleSheet("color: #10b981; font-weight: bold;")
        
        version_layout.addWidget(current_label)
        version_layout.addStretch()
        version_layout.addWidget(latest_label)
        
        layout.addWidget(version_widget)
        
        # Release notes
        notes_label = QLabel(translator.tr("Release Notes:"))
        notes_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        layout.addWidget(notes_label)
        
        notes_text = QTextEdit()
        notes_text.setReadOnly(True)
        notes_text.setMarkdown(release_notes)
        notes_text.setStyleSheet("""
            QTextEdit {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 8px;
                color: #e4e4e7;
            }
        """)
        layout.addWidget(notes_text)
        
        # Progress Bar (Hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.download_btn = QPushButton(translator.tr("Update Now") if self.is_zip else translator.tr("Download Update"))
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:pressed {
                background-color: #1e40af;
            }
        """)
        self.download_btn.clicked.connect(self.start_update)
        
        self.later_btn = QPushButton(translator.tr("Later"))
        self.later_btn.setStyleSheet("""
            QPushButton {
                background-color: #3f3f46;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #52525b;
            }
        """)
        self.later_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.later_btn)
        button_layout.addWidget(self.download_btn)
        
        layout.addLayout(button_layout)
        
    def start_update(self):
        """Start download or open browser."""
        if not self.is_zip:
            if self.download_url:
                webbrowser.open(self.download_url)
            self.accept()
            return
            
        # Start download
        self.download_btn.setEnabled(False)
        self.later_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        from core.updater import UpdateChecker
        from PySide6.QtCore import QThread, Signal
        
        class DownloadWorker(QThread):
            progress = Signal(int)
            finished = Signal(str)
            
            def __init__(self, url):
                super().__init__()
                self.url = url
                self.checker = UpdateChecker()
                
            def run(self):
                path = self.checker.download_update(self.url, self.progress.emit)
                self.finished.emit(path if path else "")
        
        self.worker = DownloadWorker(self.download_url)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.on_download_finished)
        self.worker.start()
        
    def on_download_finished(self, path):
        if not path:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, translator.tr("Error"), translator.tr("Download failed."))
            self.download_btn.setEnabled(True)
            self.later_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            return
            
        self.downloaded_file = path
        self.accept()
