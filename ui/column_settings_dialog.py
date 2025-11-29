from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QListWidget, QLabel, QListWidgetItem)
from PySide6.QtCore import Qt
from core.translator import translator

class ColumnSettingsDialog(QDialog):
    def __init__(self, available_columns, current_columns, parent=None):
        super().__init__(parent)
        self.setWindowTitle(translator.tr("Customize Columns"))
        self.resize(500, 500)
        
        self.available_columns = available_columns  # Dict: {key: display_name}
        self.current_columns = current_columns  # List of keys currently visible
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Instructions
        info = QLabel(translator.tr("✓ Check columns to display\n↕ Drag to reorder"))
        info.setStyleSheet("color: #a1a1aa; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Column list with all available columns
        self.column_list = QListWidget()
        self.column_list.setDragDropMode(QListWidget.InternalMove)
        self.populate_list()
        layout.addWidget(self.column_list)
        
        # Reset to default button
        reset_btn = QPushButton(translator.tr("Reset to Default"))
        reset_btn.clicked.connect(self.reset_to_default)
        layout.addWidget(reset_btn)
        
        # Dialog buttons
        button_row = QHBoxLayout()
        ok_btn = QPushButton(translator.tr("OK"))
        ok_btn.clicked.connect(self.accept)
        ok_btn.setProperty("class", "primary")
        
        cancel_btn = QPushButton(translator.tr("Cancel"))
        cancel_btn.clicked.connect(self.reject)
        
        button_row.addStretch()
        button_row.addWidget(ok_btn)
        button_row.addWidget(cancel_btn)
        
        layout.addLayout(button_row)
        
    def populate_list(self):
        """Populate list with all columns, checked ones first, then unchecked."""
        self.column_list.clear()
        
        # First add currently visible columns in order
        for col_key in self.current_columns:
            if col_key in self.available_columns:
                display_name = self.available_columns[col_key]
                # Translate column display name
                translated_name = translator.tr(display_name)
                item = QListWidgetItem(translated_name)
                item.setData(Qt.UserRole, col_key)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                self.column_list.addItem(item)
        
        # Then add unchecked columns
        for col_key, display_name in self.available_columns.items():
            if col_key not in self.current_columns:
                # Translate column display name
                translated_name = translator.tr(display_name)
                item = QListWidgetItem(translated_name)
                item.setData(Qt.UserRole, col_key)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                self.column_list.addItem(item)
                
    def reset_to_default(self):
        """Reset to default columns."""
        from ui.file_table import ComicTableModel
        self.current_columns = ComicTableModel.DEFAULT_COLUMNS.copy()
        self.populate_list()
        
    def get_selected_columns(self):
        """Get the final ordered list of checked column keys."""
        result = []
        for i in range(self.column_list.count()):
            item = self.column_list.item(i)
            if item.checkState() == Qt.Checked:
                col_key = item.data(Qt.UserRole)
                result.append(col_key)
        return result
