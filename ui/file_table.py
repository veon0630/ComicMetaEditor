from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSettings, QSize, QTimer
from PySide6.QtWidgets import QTableView, QHeaderView, QStyledItemDelegate, QMenu
from PySide6.QtGui import QColor, QBrush, QPixmap, QImage
from collections import OrderedDict
from core.translator import translator

class ThumbnailCache:
    """LRU cache for thumbnail pixmaps to avoid repeated image loading/scaling."""
    
    def __init__(self, max_size=200):
        self.max_size = max_size
        self.cache = OrderedDict()
    
    def get(self, key):
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        return None
    
    def set(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.max_size:
            # Remove oldest
            self.cache.popitem(last=False)

class CoverDelegate(QStyledItemDelegate):
    """Custom delegate for rendering cover thumbnails with caching."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.thumbnail_cache = ThumbnailCache(max_size=200)
        self.is_scrolling = False
        
        # Timer to detect scroll stop
        self.scroll_timer = QTimer()
        self.scroll_timer.setSingleShot(True)
        self.scroll_timer.timeout.connect(self._on_scroll_stopped)
    
    def start_scroll(self):
        """Mark that scrolling has started."""
        self.is_scrolling = True
        self.scroll_timer.stop()
    
    def stop_scroll(self):
        """Schedule scroll stop detection (delayed to avoid flicker)."""
        self.scroll_timer.start(150)  # 150ms delay
    
    def _on_scroll_stopped(self):
        """Called when scrolling has stopped."""
        self.is_scrolling = False
        # Request repaint of visible items for high quality rendering
        if self.parent():
            self.parent().viewport().update()
    
    def paint(self, painter, option, index):
        if index.column() == 0:  # Cover column
            cover_data = index.data(Qt.UserRole)
            if cover_data:
                # Create cache key from file path hash and target size
                file_obj = index.model().files[index.row()]
                target_size = option.rect.size() - QSize(4, 4)
                cache_key = (id(file_obj), target_size.width(), target_size.height())
                
                # Try to get cached thumbnail
                scaled = self.thumbnail_cache.get(cache_key)
                
                if scaled is None:
                    # Not in cache, need to load and scale
                    img = QImage.fromData(cover_data)
                    if not img.isNull():
                        pixmap = QPixmap.fromImage(img)
                        
                        # Use fast transformation during scroll, smooth when idle
                        transform_mode = Qt.FastTransformation if self.is_scrolling else Qt.SmoothTransformation
                        
                        scaled = pixmap.scaled(
                            target_size,
                            Qt.KeepAspectRatio,
                            transform_mode
                        )
                        
                        # Cache the thumbnail (always cache smooth version for reuse)
                        if not self.is_scrolling:
                            self.thumbnail_cache.set(cache_key, scaled)
                
                if scaled:
                    # Center in cell
                    x = option.rect.x() + (option.rect.width() - scaled.width()) // 2
                    y = option.rect.y() + (option.rect.height() - scaled.height()) // 2
                    
                    painter.drawPixmap(x, y, scaled)
                    return
        
        # Default rendering for other columns
        super().paint(painter, option, index)
    
    def sizeHint(self, option, index):
        if index.column() == 0:  # Cover column
            return QSize(50, 75)  # Compact thumbnail size
        return super().sizeHint(option, index)

class ComicTableModel(QAbstractTableModel):
    # All available columns
    AVAILABLE_COLUMNS = {
        "Cover": "Cover",
        "Filename": "Filename",
        "Series": "Series",
        "Number": "Number",
        "Volume": "Volume",
        "Count": "Count",
        "Title": "Title",
        "Writer": "Writer",
        "Publisher": "Publisher",
        "Year": "Year",
        "Month": "Month",
        "Day": "Day",
        "Genre": "Genre",
        "Tags": "Tags",
        "Format": "Format",
        "ISBN": "ISBN",
        "LanguageISO": "Language",
        "CommunityRating": "Rating",
        "Status": "Status",
        "Summary": "Summary",
        "Manga": "Manga",
        "Web": "Web",
    }
    
    # Default columns to display (with Cover at the beginning)
    DEFAULT_COLUMNS = ["Cover", "Filename", "Series", "Number", "Title", "Writer", "Publisher"]

    def __init__(self, files=None):
        super().__init__()
        self.files = files or []
        self.visible_columns = self.load_column_settings()

    def load_column_settings(self):
        """Load visible columns from QSettings."""
        settings = QSettings("ComicMetaEditor", "TableColumns")
        saved_columns = settings.value("visible_columns", self.DEFAULT_COLUMNS)
        
        # Validate saved columns
        if isinstance(saved_columns, list):
            # Filter out EditStatus (removed in favor of visual indicator)
            # and validate remaining columns
            valid_columns = [col for col in saved_columns 
                           if col in self.AVAILABLE_COLUMNS and col != "EditStatus"]
            return valid_columns if valid_columns else self.DEFAULT_COLUMNS.copy()
        return self.DEFAULT_COLUMNS.copy()

    def save_column_settings(self):
        """Save visible columns to QSettings."""
        settings = QSettings("ComicMetaEditor", "TableColumns")
        settings.setValue("visible_columns", self.visible_columns)

    def set_visible_columns(self, columns):
        """Update visible columns and persist the change."""
        self.beginResetModel()
        self.visible_columns = columns
        self.save_column_settings()
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self.files)

    def columnCount(self, parent=QModelIndex()):
        return len(self.visible_columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self.files):
            return None

        file_obj = self.files[index.row()]
        col_name = self.visible_columns[index.column()]

        # Cover column - return image data
        if col_name == "Cover":
            if role == Qt.UserRole:
                # Return full cover, let CoverDelegate handle scaling with cache
                return file_obj.get_cover()
            elif role == Qt.DisplayRole:
                return ""  # No text
            return None

        if role == Qt.DisplayRole:
            if col_name == "Filename":
                return file_obj.file_path.name
            else:
                value = file_obj.metadata.get(col_name, "")
                # Format certain fields
                if col_name in ["Year", "Month", "Day", "Number", "Volume", "Count"] and value:
                    return str(value)
                return value
        
        elif role == Qt.ForegroundRole:
            if col_name == "Filename":
                return QBrush(QColor("#e4e4e7")) # White-ish for filename
            return QBrush(QColor("#a1a1aa")) # Grey for others

        return None

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            col_key = self.visible_columns[section]
            original_name = self.AVAILABLE_COLUMNS.get(col_key, col_key)
            return translator.tr(original_name)
        return None

    def update_files(self, files):
        self.beginResetModel()
        self.files = files
        self.endResetModel()

    def refresh_row(self, row):
        self.dataChanged.emit(self.index(row, 0), self.index(row, len(self.visible_columns)-1))

    def refresh_headers(self):
        """Force header update for translation."""
        self.headerDataChanged.emit(Qt.Horizontal, 0, len(self.visible_columns)-1)
        # Also refresh data for "Modified" status translation
        if self.files:
            self.dataChanged.emit(self.index(0, 0), self.index(len(self.files)-1, len(self.visible_columns)-1))

class FileTable(QTableView):
    def __init__(self):
        super().__init__()
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QTableView.ExtendedSelection)
        self.setShowGrid(False)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.horizontalHeader().setStretchLastSection(True)
        self.setAlternatingRowColors(False)
        
        # Enable smooth scrolling (both vertical and horizontal)
        self.setVerticalScrollMode(QTableView.ScrollPerPixel)
        self.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        
        # Set custom delegate for cover rendering
        self.cover_delegate = CoverDelegate(self)
        self.setItemDelegate(self.cover_delegate)
        
        # Set row height to accommodate cover thumbnails (compact)
        self.verticalHeader().setDefaultSectionSize(80)
        
        # Connect scroll bar to detect scrolling for performance optimization
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)
        self.horizontalScrollBar().valueChanged.connect(self._on_scroll)
        
        # Enable context menu (right-click menu)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        self._is_scrolling = False
        self._scroll_timer = None

    def _on_scroll(self):
        """Called when scrollbar moves - optimize rendering during scroll."""
        self.cover_delegate.start_scroll()
        self.cover_delegate.stop_scroll()
    
    def _show_context_menu(self, position):
        """Show context menu on right-click."""
        # Get the MainWindow instance
        main_window = self.window()
        if not hasattr(main_window, 'scrape_act'):
            return
        
        # Create context menu with commonly used actions
        menu = QMenu(self)
        
        # Tools
        menu.addAction(main_window.scrape_act)
        menu.addAction(main_window.autonum_act)
        menu.addAction(main_window.convert_act)
        
        menu.addSeparator()
        
        # Save
        menu.addAction(main_window.save_sel_act)
        menu.addAction(main_window.save_act)
        
        menu.addSeparator()
        
        # Selection
        menu.addAction(main_window.select_all_act)
        menu.addAction(main_window.deselect_act)
        menu.addAction(main_window.invert_act)
        
        menu.exec(self.viewport().mapToGlobal(position))
    
    def paintEvent(self, event):
        """Custom paint to add green indicator for modified files."""
        # Call parent paintEvent first to draw the table normally
        super().paintEvent(event)
        
        # Now draw the green indicator bars for modified rows
        if not self.model() or not hasattr(self.model(), 'files'):
            return
        
        from PySide6.QtGui import QPainter, QPen
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Green pen for the indicator
        pen = QPen(QColor("#4CAF50"))
        pen.setWidth(5)
        painter.setPen(pen)
        
        # Only iterate through visible rows for performance
        first_visible = self.rowAt(0)
        last_visible = self.rowAt(self.viewport().height())
        
        # Handle edge cases
        if first_visible == -1:
            first_visible = 0
        if last_visible == -1:
            last_visible = self.model().rowCount() - 1
        
        # Draw indicator for each modified row that's visible
        for row in range(first_visible, last_visible + 1):
            if row >= self.model().rowCount():
                break
                
            file_obj = self.model().files[row]
            if file_obj.is_dirty:
                # Get the visual rectangle for this row
                row_rect = self.visualRect(self.model().index(row, 0))
                
                # Draw a vertical line on the left edge
                x = 0
                y1 = row_rect.top()
                y2 = row_rect.bottom()
                painter.drawLine(x, y1, x, y2)
        
        painter.end()
