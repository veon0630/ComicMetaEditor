from PySide6.QtWidgets import (
    QWidget, QLayout, QSizePolicy, QLabel, QPushButton, 
    QHBoxLayout, QVBoxLayout, QLineEdit, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, QRect, QSize, QPoint, Signal

class FlowLayout(QLayout):
    """Flow layout that wraps widgets to multiple lines."""
    
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.itemList = []

    def __del__(self):
        while self.takeAt(0):
            pass

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        if not self.itemList:
            return QSize(0, 0)
        
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def doLayout(self, rect, testOnly):
        if not self.itemList:
            return 0
        
        x = rect.x()
        y = rect.y()
        lineHeight = 0
        spacing = self.spacing()
        
        # Calculate available width
        effective_width = rect.width()

        for item in self.itemList:
            widget = item.widget()
            if not widget:
                continue
            
            style = widget.style()
            spaceX = spacing + style.layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal)
            spaceY = spacing + style.layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical)
            
            nextX = x + item.sizeHint().width() + spaceX
            
            # Wrap to next line if needed
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y += lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()


class TagChip(QFrame):
    """A single tag chip with label and remove button."""
    
    removed = Signal(str)

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.text = text
        self.setStyleSheet("""
            TagChip {
                background-color: #2d2d2d;
                border: 1px solid #52525b;
                border-radius: 12px;
            }
            QLabel {
                color: #e4e4e7;
                font-weight: 500;
                border: none;
                background: transparent;
            }
            QPushButton {
                background: transparent;
                border: none;
                color: #71717a;
                font-weight: bold;
                padding: 0;
                margin: 0;
            }
            QPushButton:hover {
                color: #ef4444;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        self.label = QLabel(text)
        self.label.setWordWrap(True)
        # Allow label to shrink if needed, but prefer expanding
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self.label)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(16, 16)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(lambda: self.removed.emit(self.text))
        # Button shouldn't expand
        close_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout.addWidget(close_btn)
        
        # Chip itself should be able to expand horizontally if needed (up to max width)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)


class TagEditor(QWidget):
    """Tag editor with scrollable pill-style tags and add/remove functionality."""
    
    tagsChanged = Signal(str)  # Emits comma-separated string

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tags = []
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Scroll Area for Tags
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setFixedHeight(120)  # Fixed height for the scroll area
        # Updated background color to match inputs (#252526)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 4px;
            }
            QWidget#tags_container {
                background-color: transparent;
            }
        """)

        self.tags_container = QWidget()
        self.tags_container.setObjectName("tags_container")
        self.flow_layout = FlowLayout(self.tags_container, margin=4, spacing=4)
        self.scroll_area.setWidget(self.tags_container)
        
        layout.addWidget(self.scroll_area)

        # Input Area
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(8)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Add new tag...")
        self.input_field.returnPressed.connect(self.add_tag)
        input_layout.addWidget(self.input_field)

        add_btn = QPushButton("+")
        add_btn.setFixedSize(40, 30)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet("font-size: 20px; padding: 0px; padding-bottom: 5px;")
        add_btn.clicked.connect(self.add_tag)
        input_layout.addWidget(add_btn)

        layout.addLayout(input_layout)

    def resizeEvent(self, event):
        """Handle resize to update tag chip widths."""
        super().resizeEvent(event)
        self._update_chip_widths()

    def _update_chip_widths(self):
        """Update maximum width of all tag chips to fit in viewport."""
        # Calculate available width in the viewport
        # Subtract margins and scrollbar width if visible
        viewport_width = self.scroll_area.viewport().width()
        # Safety margin
        max_width = max(50, viewport_width - 20)
        
        for i in range(self.flow_layout.count()):
            item = self.flow_layout.itemAt(i)
            if item and item.widget():
                item.widget().setMaximumWidth(max_width)

    def setTags(self, tags_str):
        """Set tags from comma-separated string."""
        # Clear existing widgets
        while self.flow_layout.count():
            item = self.flow_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Parse and create new tags
        self.tags = []
        if tags_str:
            new_tags = [t.strip() for t in str(tags_str).split(',') if t.strip()]
            for tag in new_tags:
                self._create_tag_chip(tag)
                self.tags.append(tag)
        
        # Update widths after adding
        self._update_chip_widths()

    def add_tag(self):
        """Add a new tag from input field."""
        text = self.input_field.text().strip()
        if not text:
            return
        
        if text in self.tags:
            self.input_field.clear()
            return
        
        self.tags.append(text)
        self._create_tag_chip(text)
        self.input_field.clear()
        self.tagsChanged.emit(",".join(self.tags))
        
        # Update widths
        self._update_chip_widths()
        
        # Scroll to bottom to show new tag
        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())

    def _create_tag_chip(self, text):
        """Helper to create and add a tag chip."""
        chip = TagChip(text, self.tags_container)
        chip.removed.connect(self.remove_tag)
        self.flow_layout.addWidget(chip)

    def remove_tag(self, text):
        """Remove a tag."""
        if text in self.tags:
            self.setTags(",".join(t for t in self.tags if t != text))
            self.tagsChanged.emit(",".join(self.tags))

    def text(self):
        """Get comma-separated tag string."""
        return ",".join(self.tags)
