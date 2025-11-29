"""
Update notification dialog for displaying available updates.
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTextEdit, QWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import webbrowser

from core.translator import translator


class UpdateDialog(QDialog):
    """Dialog to show update information and provide download link."""
    
    def __init__(self, current_version, latest_version, release_notes, download_url, parent=None):
        super().__init__(parent)
        self.download_url = download_url
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
        notes_text.setPlainText(release_notes)
        notes_text.setStyleSheet("""
            QTextEdit {
                background-color: #27272a;
                border: 1px solid #3f3f46;
                border-radius: 4px;
                padding: 8px;
                color: #e4e4e7;
            }
        """)
        layout.addWidget(notes_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        download_btn = QPushButton(translator.tr("Download Update"))
        download_btn.setStyleSheet("""
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
        download_btn.clicked.connect(self.open_download)
        
        later_btn = QPushButton(translator.tr("Later"))
        later_btn.setStyleSheet("""
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
        later_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(later_btn)
        button_layout.addWidget(download_btn)
        
        layout.addLayout(button_layout)
        
    def open_download(self):
        """Open the download URL in the default browser."""
        if self.download_url:
            webbrowser.open(self.download_url)
        self.accept()
