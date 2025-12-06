from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QGroupBox, QMessageBox)
from PySide6.QtCore import Qt
from core.settings_manager import settings_manager
from core.translator import translator

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(translator.tr("Bangumi Settings"))
        self.setMinimumWidth(400)  # Set minimum width instead of fixed size
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)  # Reduce default margins
        
        # Access Token Group
        group = QGroupBox(translator.tr("Access Token"))
        group.setStyleSheet("""
            QGroupBox {
                padding-top: 10px;
                margin-top: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
            }
        """)
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(10, 0, 10, 10)
        
        help_label = QLabel(translator.tr("Enter your Bangumi Access Token to increase rate limits and access NSFW content."))
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #a1a1aa; font-size: 12px;")
        group_layout.addWidget(help_label)
        
        # Guide label with clickable link
        guide_label = QLabel(translator.tr("token_guide_html"))
        guide_label.setTextFormat(Qt.RichText)
        guide_label.setWordWrap(True)
        guide_label.setOpenExternalLinks(True)
        guide_label.setStyleSheet("color: #71717a; font-size: 11px;")
        group_layout.addWidget(guide_label)
        
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Access Token")
        self.token_input.setText(settings_manager.get("bangumi_token", ""))
        self.token_input.setEchoMode(QLineEdit.Password)
        group_layout.addWidget(self.token_input)
        
        # Show/Hide Token Button
        btn_row_token = QHBoxLayout()
        self.show_token_btn = QPushButton(translator.tr("Show Token"))
        self.show_token_btn.setCheckable(True)
        self.show_token_btn.toggled.connect(self.toggle_token_visibility)
        
        self.test_token_btn = QPushButton(translator.tr("Test Token"))
        self.test_token_btn.clicked.connect(self.test_token)
        
        btn_row_token.addWidget(self.show_token_btn)
        btn_row_token.addWidget(self.test_token_btn)
        group_layout.addLayout(btn_row_token)
        
        layout.addWidget(group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton(translator.tr("Save"))
        save_btn.clicked.connect(self.save_settings)
        save_btn.setProperty("class", "primary")
        
        cancel_btn = QPushButton(translator.tr("Cancel"))
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
        
    def toggle_token_visibility(self, checked):
        if checked:
            self.token_input.setEchoMode(QLineEdit.Normal)
            self.show_token_btn.setText(translator.tr("Hide Token"))
        else:
            self.token_input.setEchoMode(QLineEdit.Password)
            self.show_token_btn.setText(translator.tr("Show Token"))

    def test_token(self):
        token = self.token_input.text().strip()
        if not token:
            QMessageBox.warning(self, translator.tr("Warning"), translator.tr("Please enter a token first."))
            return
            
        self.test_token_btn.setEnabled(False)
        self.test_token_btn.setText(translator.tr("Testing..."))
        
        import requests
        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "User-Agent": "DAZAO/ComicMetaEditor"
            }
            # Use /v0/me to check user info
            resp = requests.get("https://api.bgm.tv/v0/me", headers=headers, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                username = data.get("nickname") or data.get("username")
                user_id = data.get("id")
                QMessageBox.information(self, translator.tr("Success"), 
                    translator.tr("Token is valid!\n\nUser: {}\nID: {}").format(username, user_id))
            elif resp.status_code == 401:
                QMessageBox.critical(self, translator.tr("Error"), translator.tr("Invalid token. Please check and try again."))
            else:
                QMessageBox.critical(self, translator.tr("Error"), 
                    translator.tr("Token test failed (HTTP {}).").format(resp.status_code))
                    
        except Exception as e:
            QMessageBox.critical(self, translator.tr("Error"), translator.tr("Connection failed: {}").format(str(e)))
        finally:
            self.test_token_btn.setEnabled(True)
            self.test_token_btn.setText(translator.tr("Test Token"))
            
    def save_settings(self):
        token = self.token_input.text().strip()
        settings_manager.set("bangumi_token", token)
        self.accept()
