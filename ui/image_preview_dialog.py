from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QSizePolicy, QMenu
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage, QResizeEvent
from core.translator import translator


class ImagePreviewDialog(QDialog):
    """Dialog for previewing images with adaptive scaling."""
    
    def __init__(self, image_data, parent=None):
        super().__init__(parent)
        self.image_data = image_data
        self.original_pixmap = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle(translator.tr("Cover Preview"))
        self.resize(500, 700)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Image label
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #18181b;")
        # Allow label to shrink below image size to prevent window from being forced large
        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        
        layout.addWidget(self.image_label)
        
        # Apply dark theme styling
        self.setStyleSheet("""
            QDialog {
                background-color: #18181b;
            }
            QLabel {
                color: #fafafa;
            }
            QMenu {
                background-color: #2d2d30;
                color: #fafafa;
                border: 1px solid #3e3e42;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #3e3e42;
            }
        """)
        
        # Load image
        if self.image_data:
            img = QImage.fromData(self.image_data)
            if not img.isNull():
                self.original_pixmap = QPixmap.fromImage(img)
                # Initial update will happen in showEvent/resizeEvent
                self.update_image()
            else:
                self.image_label.setText(translator.tr("Invalid Image"))
        else:
            self.image_label.setText(translator.tr("No Image"))

        # Enable context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def mouseDoubleClickEvent(self, event):
        """Close dialog on double click."""
        self.close()

    def show_context_menu(self, pos):
        if not self.original_pixmap:
            return
            
        menu = QMenu(self)
        save_action = menu.addAction(translator.tr("Save Image As..."))
        copy_action = menu.addAction(translator.tr("Copy Image"))
        
        action = menu.exec(self.mapToGlobal(pos))
        
        if action == save_action:
            self.save_image()
        elif action == copy_action:
            self.copy_image()
            
    def save_image(self):
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            translator.tr("Save Image"),
            "cover.jpg",
            "Images (*.jpg *.png *.webp)"
        )
        if file_path:
            self.original_pixmap.save(file_path)
            
    def copy_image(self):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setPixmap(self.original_pixmap)

            
    def resizeEvent(self, event: QResizeEvent):
        """Handle window resize events to rescale the image."""
        self.update_image()
        super().resizeEvent(event)
        
    def update_image(self):
        """Scale the image to fit the current label size."""
        if self.original_pixmap and not self.original_pixmap.isNull():
            size = self.image_label.size()
            if size.width() > 0 and size.height() > 0:
                scaled_pixmap = self.original_pixmap.scaled(
                    size, 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                self.image_label.setPixmap(scaled_pixmap)
