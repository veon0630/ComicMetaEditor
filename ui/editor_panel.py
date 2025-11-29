from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QScrollArea, QFormLayout,
    QComboBox, QGroupBox, QPushButton, QMenu,
    QWidgetAction, QCalendarWidget, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QDate, QUrl
from PySide6.QtGui import QPixmap, QImage, QCursor, QDesktopServices
from ui.tag_editor import TagEditor
from ui.image_preview_dialog import ImagePreviewDialog
from utils.logger import logger
from core.translator import translator

class EditorPanel(QWidget):
    metadataChanged = Signal(str, str)  # key, value

    def __init__(self):
        super().__init__()
        self.current_files = []
        self.labels = {}  # Store labels for translation
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        content = QWidget()
        main_layout = QVBoxLayout(content)
        main_layout.setSpacing(10)

        # Cover Image
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(170, 250)  # Reduced size to align better
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setStyleSheet("background-color: #18181b; border: 1px solid #3e3e42; border-radius: 8px;")
        self.cover_label.setText("No Cover")
        self.cover_label.setCursor(Qt.PointingHandCursor)  # Change cursor to hand on hover
        self.cover_label.mousePressEvent = self.on_cover_clicked  # Make it clickable

        # Upload Cover Button
        self.upload_cover_btn = QPushButton(translator.tr("Upload Cover"))
        self.upload_cover_btn.clicked.connect(self.upload_cover)
        self.upload_cover_btn.setMaximumWidth(170)  # Match cover width

        # Cover container
        cover_container = QVBoxLayout()
        cover_container.addWidget(self.cover_label)
        cover_container.addWidget(self.upload_cover_btn)
        cover_container.setAlignment(Qt.AlignTop)

        # Top Section (Cover + Series Info)
        top_section = QHBoxLayout()
        top_section.addLayout(cover_container)

        # Series & Issue Group (Right of Cover)
        series_widget = QWidget()
        self.form_layout = QFormLayout(series_widget)  # Set current form layout
        self.form_layout.setContentsMargins(10, 0, 0, 0)
        self.form_layout.setVerticalSpacing(8)  # Increase row spacing

        self.inputs = {}

        self.add_group("Series & Issue")
        self.add_field("Series", "Series")
        self.add_field("Title", "Title")
        self.add_field("Number", "Number")
        self.add_field("Volume", "Volume")
        self.add_field("Count", "Count")
        self.add_field("Status", "Status", is_combo=True, options=["", "Ongoing", "Ended", "Abandoned", "Hiatus"]) 
        
        # Add stretch to align with cover if needed, or just let it be
        # The form layout naturally packs items.

        top_section.addWidget(series_widget)
        main_layout.addLayout(top_section)

        # Credits & Publication Group
        credits_widget = QWidget()
        self.form_layout = QFormLayout(credits_widget)  # Switch layout
        self.form_layout.setVerticalSpacing(8)  # Increase row spacing

        self.add_group("Credits & Publication")
        self.add_field("Writer", "Writer")
        self.add_field("Publisher", "Publisher")
        self.add_field("ISBN", "ISBN")
        self.add_date_row("Date", ["Year", "Month", "Day"])
        self.add_field("Language", "LanguageISO", is_combo=True, options=["", "zho", "jpn", "eng"])
        self.add_field("Format", "Format")

        main_layout.addWidget(credits_widget)

        # Content & Details Group
        details_widget = QWidget()
        self.form_layout = QFormLayout(details_widget)  # Switch layout
        self.form_layout.setVerticalSpacing(8)  # Increase row spacing

        self.add_group("Content & Details")
        
        # Genre and Tags side-by-side
        genre_tags_layout = QHBoxLayout()
        genre_tags_layout.setSpacing(10)
        
        # Genre Column
        genre_container = QWidget()
        genre_layout = QVBoxLayout(genre_container)
        genre_layout.setContentsMargins(0, 0, 0, 0)
        genre_layout.setSpacing(4)
        genre_layout.setSpacing(4)
        self.genre_label = QLabel(translator.tr("Genre"))
        genre_layout.addWidget(self.genre_label)
        self.genre_editor = TagEditor()
        self.genre_editor.tagsChanged.connect(lambda: self.on_field_changed("Genre"))
        genre_layout.addWidget(self.genre_editor)
        self.inputs["Genre"] = self.genre_editor
        genre_tags_layout.addWidget(genre_container)
        
        # Tags Column
        tags_container = QWidget()
        tags_layout = QVBoxLayout(tags_container)
        tags_layout.setContentsMargins(0, 0, 0, 0)
        tags_layout.setSpacing(4)
        tags_layout.setSpacing(4)
        self.tags_label = QLabel(translator.tr("Tags"))
        tags_layout.addWidget(self.tags_label)
        self.tags_editor = TagEditor()
        self.tags_editor.tagsChanged.connect(lambda: self.on_field_changed("Tags"))
        tags_layout.addWidget(self.tags_editor)
        self.inputs["Tags"] = self.tags_editor
        genre_tags_layout.addWidget(tags_container)
        
        self.form_layout.addRow(genre_tags_layout)

        # Summary moved below Genre/Tags and increased height
        self.add_field("Summary", "Summary", is_text_area=True, height=150)

        self.add_field("Rating", "CommunityRating")
        self.add_field("Manga", "Manga", is_combo=True, options=["YesAndRightToLeft", "No", "Yes"])
        self.add_field("Web", "Web", is_link=True)

        main_layout.addWidget(details_widget)
        main_layout.addStretch()  # Push everything up

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def add_group(self, title):
        group_label = QLabel(translator.tr(title))
        group_label.setProperty("class", "header")
        self.form_layout.addRow(group_label)
        self.labels[title] = group_label  # Store using original title as key

    def add_field(self, label, key, is_text_area=False, is_combo=False, options=None, is_link=False, is_tag_editor=False, height=None):
        lbl = QLabel(translator.tr(label))
        self.labels[label] = lbl  # Store using original label as key
        if is_text_area:
            widget = QTextEdit()
            # Use provided height or default to 100
            widget.setMinimumHeight(height if height else 100)
            # Remove maximum height restriction or set it larger if needed, but minimum is usually better for text areas
            # to prevent them from being too small. Let's set a fixed height for consistency if desired, 
            # or just min height. The user asked to "increase height", implying it was too small.
            if height:
                widget.setFixedHeight(height)
            else:
                widget.setMaximumHeight(100) 
            widget.textChanged.connect(lambda: self.on_field_changed(key))
        elif is_combo:
            widget = QComboBox()
            widget.addItems(options or [])
            widget.currentTextChanged.connect(lambda: self.on_field_changed(key))
        elif is_tag_editor:
            widget = TagEditor()
            widget.tagsChanged.connect(lambda: self.on_field_changed(key))
        else:
            widget = QLineEdit()
            widget.textChanged.connect(lambda: self.on_field_changed(key))
        if is_link:
            h_layout = QHBoxLayout()
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.setSpacing(10)
            h_layout.addWidget(widget, 1)
            link_btn = QPushButton("🔗")
            link_btn.setFixedSize(40, 30)
            link_btn.setCursor(Qt.PointingHandCursor)
            link_btn.setToolTip("Open Link")
            link_btn.clicked.connect(lambda: self.open_web_link(widget.text()))
            h_layout.addWidget(link_btn)
            self.form_layout.addRow(lbl, h_layout)
        else:
            self.form_layout.addRow(lbl, widget)
        self.inputs[key] = widget

    def open_web_link(self, url):
        if url:
            if not url.startswith("http"):
                url = "https://" + url
            QDesktopServices.openUrl(QUrl(url))

    def add_date_row(self, label, keys):
        lbl = QLabel(translator.tr(label))
        self.labels[label] = lbl
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        placeholders = ["YYYY", "MM", "DD"]
        for i, key in enumerate(keys):
            widget = QLineEdit()
            widget.setPlaceholderText(placeholders[i])
            widget.textChanged.connect(lambda text, k=key: self.on_field_changed(k))
            layout.addWidget(widget)
            self.inputs[key] = widget
        cal_btn = QPushButton("📅")
        cal_btn.setFixedSize(40, 30)
        cal_btn.setCursor(Qt.PointingHandCursor)
        cal_btn.clicked.connect(self.show_date_picker)
        layout.addWidget(cal_btn)
        self.form_layout.addRow(lbl, layout)

    def show_date_picker(self):
        menu = QMenu(self)
        cal = QCalendarWidget()
        try:
            y = int(self.inputs["Year"].text())
            m = int(self.inputs["Month"].text())
            d = int(self.inputs["Day"].text())
            cal.setSelectedDate(QDate(y, m, d))
        except (ValueError, KeyError):
            cal.setSelectedDate(QDate.currentDate())
        cal.clicked.connect(lambda date: self.on_date_picked(date, menu))
        action = QWidgetAction(menu)
        action.setDefaultWidget(cal)
        menu.addAction(action)
        menu.exec(QCursor.pos())

    def on_date_picked(self, date, menu):
        self.inputs["Year"].setText(str(date.year()))
        self.inputs["Month"].setText(str(date.month()))
        self.inputs["Day"].setText(str(date.day()))
        menu.close()

    def load_selection(self, files):
        self.current_files = files
        self.block_signals(True)
        if not files:
            self.clear_form()
            self.cover_label.setText(translator.tr("No Selection"))
            self.cover_label.setPixmap(QPixmap())
        else:
            first = files[0]
            for key, widget in self.inputs.items():
                val = first.metadata.get(key, "")
                if isinstance(widget, QLineEdit):
                    widget.setText(str(val))
                elif isinstance(widget, QTextEdit):
                    widget.setPlainText(str(val))
                elif isinstance(widget, QComboBox):
                    idx = widget.findText(str(val))
                    widget.setCurrentIndex(idx if idx >= 0 else -1)
                elif isinstance(widget, TagEditor):
                    widget.setTags(str(val))
            # Use thumbnail instead of full cover to save memory
            cover_data = first.get_cover_thumbnail(max_size=(200, 300))
            if cover_data:
                img = QImage.fromData(cover_data)
                if not img.isNull():
                    pixmap = QPixmap.fromImage(img)
                    self.cover_label.setPixmap(pixmap.scaled(self.cover_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    self.cover_label.setText("")
                else:
                    self.cover_label.setText("Invalid Image")
            else:
                self.cover_label.setText(translator.tr("No Cover"))
                self.cover_label.setPixmap(QPixmap())
        self.block_signals(False)

    def block_signals(self, block):
        for widget in self.inputs.values():
            widget.blockSignals(block)

    def clear_form(self):
        for widget in self.inputs.values():
            if isinstance(widget, (QLineEdit, QTextEdit)):
                widget.clear()
            elif isinstance(widget, QComboBox):
                widget.setCurrentIndex(-1)
            elif isinstance(widget, TagEditor):
                widget.setTags("")

    def on_field_changed(self, key):
        if not self.current_files:
            return
        widget = self.inputs[key]
        if isinstance(widget, QLineEdit):
            value = widget.text()
        elif isinstance(widget, QTextEdit):
            value = widget.toPlainText()
        elif isinstance(widget, QComboBox):
            value = widget.currentText()
        elif isinstance(widget, TagEditor):
            value = widget.text()
        else:
            value = ""
        self.metadataChanged.emit(key, value)

    def upload_cover(self):
        if not self.current_files:
            return
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            translator.tr("Select Cover Image"),
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.gif *.bmp)"
        )
        if file_path:
            logger.info(f"User uploaded custom cover from: {file_path}")
            try:
                with open(file_path, 'rb') as f:
                    cover_data = f.read()
                for file_obj in self.current_files:
                    file_obj.set_custom_cover(cover_data)
                img = QImage.fromData(cover_data)
                if not img.isNull():
                    pixmap = QPixmap.fromImage(img)
                    self.cover_label.setPixmap(pixmap.scaled(self.cover_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    self.cover_label.setText("")
            except Exception as e:
                logger.error(f"Error uploading cover: {e}")
    
    def on_cover_clicked(self, event):
        """Handle click on cover image to show full-size preview."""
        if not self.current_files or not self.current_files[0]:
            return
        
        # Get full cover data (not thumbnail)
        cover_data = self.current_files[0].get_cover()
        if cover_data:
            dialog = ImagePreviewDialog(cover_data, self)
            dialog.exec()


    def retranslate_ui(self):
        """Update UI texts based on current language."""
        # Update group and field labels
        for key, label_widget in self.labels.items():
            label_widget.setText(translator.tr(key))
            
        # Update static labels
        self.genre_label.setText(translator.tr("Genre"))
        self.tags_label.setText(translator.tr("Tags"))
        self.upload_cover_btn.setText(translator.tr("Upload Cover"))
        
        # Update dynamic labels based on state
        if not self.current_files:
            self.cover_label.setText(translator.tr("No Selection"))
        elif self.cover_label.text() in ["No Cover", "表紙なし", "无封面"]: # Check against known translations or just reset if empty
             # If it was "No Cover" (translated), update it. 
             # But checking translated text is hard. 
             # Simpler: if pixmap is null and text is not empty, it's likely a status message.
             # But we can just rely on load_selection to be called or user interaction.
             # For now, let's just update if it matches the "No Cover" key in any language? No.
             # Let's just re-run load_selection logic if possible? No, too heavy.
             # Just leave it, it will update on next selection change.
             pass
