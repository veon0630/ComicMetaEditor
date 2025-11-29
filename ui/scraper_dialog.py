from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
                               QPushButton, QListWidget, QListWidgetItem, QLabel, 
                               QWidget, QMessageBox, QProgressBar, QStackedWidget,
                               QSplitter, QTextEdit, QCheckBox, QComboBox)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QPixmap, QImage

from core.scraper import BangumiScraper
import requests
from core.translator import translator

class SearchThread(QThread):
    resultsReady = Signal(list)
    errorOccurred = Signal(str)
    statusUpdate = Signal(str)

    def __init__(self, scraper, query):
        super().__init__()
        self.scraper = scraper
        self.query = query
        self._is_cancelled = False

    def run(self):
        try:
            if self._is_cancelled:
                return
            self.statusUpdate.emit(translator.tr("Connecting to Bangumi API..."))
            results = self.scraper.search_subjects(self.query)
            if self._is_cancelled:
                return
            self.statusUpdate.emit(translator.tr("Found {} results").format(len(results)))
            self.resultsReady.emit(results)
        except Exception as e:
            if not self._is_cancelled:
                self.errorOccurred.emit(str(e))
    
    def cancel(self):
        self._is_cancelled = True

class VolumeThread(QThread):
    volumesReady = Signal(list)
    errorOccurred = Signal(str)
    statusUpdate = Signal(str)

    def __init__(self, scraper, subject_id):
        super().__init__()
        self.scraper = scraper
        self.subject_id = subject_id
        self._is_cancelled = False

    def run(self):
        try:
            if self._is_cancelled:
                return
            self.statusUpdate.emit(translator.tr("Fetching volume list..."))
            # Fetch related subjects
            # We want single volumes (Offprints)
            related = self.scraper.get_related_subjects(self.subject_id)
            if self._is_cancelled:
                return
            # Filter for volumes (relation "单行本" or similar)
            volumes = [r for r in related if r.get("relation") in ["单行本", "前传", "续集", "番外篇"]]
            for v in volumes:
                v["type_label"] = "Volume"
            # Sort by ID or Name? Usually Bangumi returns in some order.
            # Let's trust the API order or sort by name.
            self.statusUpdate.emit(translator.tr("Found {} volumes").format(len(volumes)))
            self.volumesReady.emit(volumes)
        except Exception as e:
            if not self._is_cancelled:
                self.errorOccurred.emit(str(e))
    
    def cancel(self):
        self._is_cancelled = True

class ImageLoader(QThread):
    imageLoaded = Signal(QPixmap)
    errorOccurred = Signal(str)
    
    def __init__(self, url, timeout=10):
        super().__init__()
        self.url = url
        self.timeout = timeout
        self._is_cancelled = False
        
    def run(self):
        try:
            if not self.url or self._is_cancelled:
                return
            resp = requests.get(self.url, timeout=self.timeout)
            if self._is_cancelled:
                return
            resp.raise_for_status()
            img = QImage.fromData(resp.content)
            if not img.isNull() and not self._is_cancelled:
                self.imageLoaded.emit(QPixmap.fromImage(img))
        except requests.exceptions.Timeout:
            if not self._is_cancelled:
                self.errorOccurred.emit(translator.tr("Image load timeout"))
        except requests.exceptions.ConnectionError:
            if not self._is_cancelled:
                self.errorOccurred.emit(translator.tr("Connection failed"))
        except Exception as e:
            if not self._is_cancelled:
                self.errorOccurred.emit(translator.tr("Failed to load image: {}").format(str(e)))
    
    def cancel(self):
        self._is_cancelled = True

# ==================== Helper Functions ====================

def extract_infobox_value(infobox, key):
    """
    从 Bangumi infobox 中提取指定键的值
    
    Args:
        infobox: infobox 数组
        key: 要查找的键名
        
    Returns:
        提取的值，如果未找到返回 None
    """
    if not infobox:
        return None
    
    for item in infobox:
        if item.get("key") == key:
            val = item.get("value")
            # 处理不同类型的值
            if isinstance(val, list):
                # 处理列表类型的值
                result = []
                for v in val:
                    if isinstance(v, dict):
                        result.append(v.get("v", ""))
                    else:
                        result.append(str(v))
                return ", ".join(result) if result else None
            elif isinstance(val, dict):
                return val.get("v", str(val))
            else:
                return str(val) if val else None
    return None

def format_rating_info(data):
    """
    格式化评分信息显示
    
    Args:
        data: 包含评分信息的数据字典
        
    Returns:
        格式化的评分字符串
    """
    parts = []
    
    # 评分
    if "rating" in data and isinstance(data["rating"], dict):
        rating_data = data["rating"]
        score = rating_data.get("score")
        if score:
            parts.append(f"⭐ {score}")
            
            # 评分人数
            count = rating_data.get("total")
            if count:
                parts.append(f"({count} ratings)")
            
            # 排名
            rank = rating_data.get("rank")
            if rank:
                parts.append(f"Rank #{rank}")
    elif "score" in data:
        # 兼容旧格式
        parts.append(f"⭐ {data['score']}")
    
    return " ".join(parts) if parts else None

def format_collection_info(data):
    """
    格式化收藏信息显示
    
    Args:
        data: 包含收藏信息的数据字典
        
    Returns:
        格式化的收藏字符串
    """
    if "collection" in data and isinstance(data["collection"], dict):
        total = data["collection"].get("collect", 0)
        if total > 0:
            if total >= 10000:
                return f"📚 {total/10000:.1f}万收藏"
            else:
                return f"📚 {total}收藏"
    return None

def extract_author_info(infobox):
    """
    从 infobox 提取作者信息
    
    Args:
        infobox: infobox 数组
        
    Returns:
        作者信息字符串
    """
    authors = []
    
    # 尝试多个可能的键名
    for key in ["作者", "漫画", "著者", "原作", "作画"]:
        value = extract_infobox_value(infobox, key)
        if value and value not in authors:
            authors.append(value)
    
    return " / ".join(authors[:2]) if authors else None  # 最多显示2个作者

def extract_publisher_info(infobox):
    """
    从 infobox 提取出版社信息
    
    Args:
        infobox: infobox 数组
        
    Returns:
        出版社信息字符串
    """
    return extract_infobox_value(infobox, "出版社") or extract_infobox_value(infobox, "中文出版社")

def extract_volume_count(infobox):
    """
    从 infobox 提取卷数信息
    
    Args:
        infobox: infobox 数组
        
    Returns:
        卷数字符串
    """
    count = extract_infobox_value(infobox, "话数") or extract_infobox_value(infobox, "卷数")
    if count:
        # 尝试提取数字
        import re
        match = re.search(r'\d+', str(count))
        if match:
            return f"{match.group()}卷"
    return None

def extract_status_info(data):
    """
    提取连载状态信息
    
    Args:
        data: 元数据字典
        
    Returns:
        状态字符串和颜色
    """
    # 从 tags 中查找状态
    tags = data.get("tags", [])
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, dict):
                name = tag.get("name", "")
                if "连载" in name:
                    return ("连载中", "#10b981")
                elif "完结" in name or "已完结" in name:
                    return ("已完结", "#6b7280")
    
    # 从 infobox 查找
    infobox = data.get("infobox", [])
    status = extract_infobox_value(infobox, "连载状态") or extract_infobox_value(infobox, "状态")
    if status:
        if "连载" in status:
            return (status, "#10b981")
        elif "完结" in status:
            return (status, "#6b7280")
        return (status, "#71717a")
    
    return None

class ResultItemWidget(QWidget):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        
        self.image_loader = None  # Track image loader thread
        
        # Cover
        self.cover_lbl = QLabel()
        self.cover_lbl.setFixedSize(50, 75)
        self.cover_lbl.setStyleSheet("background-color: #333; border: 1px solid #444; border-radius: 4px;")
        self.cover_lbl.setScaledContents(True)
        layout.addWidget(self.cover_lbl)
        
        # Load cover async
        images = data.get("images") or data.get("image")
        if images and isinstance(images, dict):
            url = images.get("common") or images.get("medium") or images.get("grid")
            if url:
                if url.startswith("//"): url = "https:" + url
                self.image_loader = ImageLoader(url)
                self.image_loader.imageLoaded.connect(self.cover_lbl.setPixmap)
                self.image_loader.finished.connect(self.image_loader.deleteLater)
                self.image_loader.start()
        
        # Info Layout (右侧所有信息)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        # ========== 第一行：标题 + 徽章 ==========
        title_row = QHBoxLayout()
        title_row.setSpacing(6)
        
        title_txt = data.get("name_cn") or data.get("name")
        title = QLabel(title_txt)
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #e4e4e7;")
        title.setWordWrap(False)
        title_row.addWidget(title, 1)
        
        # Type Badge (Series/Volume)
        type_label = data.get("type_label", "Unknown")
        badge_color = "#3b82f6" if type_label == "Series" else "#71717a"
        badge = QLabel(f" {type_label} ")
        badge.setStyleSheet(f"background-color: {badge_color}; color: white; border-radius: 3px; padding: 2px 6px; font-size: 10px; font-weight: bold;")
        badge.setFixedHeight(18)
        title_row.addWidget(badge)
        
        # Platform Badge (漫画/小说/画集)
        platform = data.get("platform", "")
        if platform:
            platform_colors = {
                "漫画": "#10b981",  # Green
                "小说": "#f59e0b",  # Orange
                "画集": "#8b5cf6",  # Purple
            }
            platform_color = platform_colors.get(platform, "#6b7280")
            platform_badge = QLabel(f" {platform} ")
            platform_badge.setStyleSheet(f"background-color: {platform_color}; color: white; border-radius: 3px; padding: 2px 6px; font-size: 10px; font-weight: bold;")
            platform_badge.setFixedHeight(18)
            title_row.addWidget(platform_badge)
        
        # Status Badge (连载中/已完结)
        status_info = extract_status_info(data)
        if status_info:
            status_text, status_color = status_info
            status_badge = QLabel(f" {status_text} ")
            status_badge.setStyleSheet(f"background-color: {status_color}; color: white; border-radius: 3px; padding: 2px 6px; font-size: 10px;")
            status_badge.setFixedHeight(18)
            title_row.addWidget(status_badge)
        
        title_row.addStretch()
        info_layout.addLayout(title_row)
        
        # ========== 第二行：原文标题 ==========
        orig_name = data.get("name")
        if orig_name and orig_name != title_txt:
            orig_title = QLabel(orig_name)
            orig_title.setStyleSheet("color: #a1a1aa; font-size: 12px;")
            orig_title.setWordWrap(False)
            info_layout.addWidget(orig_title)
        
        # ========== 第三行：作者 + 出版社 ==========
        infobox = data.get("infobox", [])
        author_publisher_parts = []
        
        author = extract_author_info(infobox)
        if author:
            author_publisher_parts.append(f"✍ {author}")
        
        publisher = extract_publisher_info(infobox)
        if publisher:
            author_publisher_parts.append(f"📖 {publisher}")
        
        if author_publisher_parts:
            author_publisher_label = QLabel(" · ".join(author_publisher_parts))
            author_publisher_label.setStyleSheet("color: #a1a1aa; font-size: 11px;")
            author_publisher_label.setWordWrap(False)
            info_layout.addWidget(author_publisher_label)
        
        # ========== 第四行：评分 + 收藏 + 日期 + ID ==========
        details_parts = []
        
        # 评分信息
        rating_str = format_rating_info(data)
        if rating_str:
            details_parts.append(rating_str)
        
        # 收藏数
        collection_str = format_collection_info(data)
        if collection_str:
            details_parts.append(collection_str)
        
        # 卷数（仅 Series）
        if data.get("type_label") == "Series":
            volume_count = extract_volume_count(infobox)
            if volume_count:
                details_parts.append(f"📚 {volume_count}")
        
        # 日期
        if "date" in data and data["date"]:
            details_parts.append(f"📅 {data['date']}")
        
        # ID
        if "id" in data:
            details_parts.append(f"ID: {data['id']}")
        
        if details_parts:
            details = QLabel(" · ".join(details_parts))
            details.setStyleSheet("color: #71717a; font-size: 11px;")
            details.setWordWrap(True)
            info_layout.addWidget(details)
        
        layout.addLayout(info_layout, 1)

class ScraperDialog(QDialog):
    metadataSelected = Signal(dict, str, dict) # metadata, type, options

    def __init__(self, parent=None, initial_query=""):
        super().__init__(parent)
        self.setWindowTitle(translator.tr("Bangumi Scraper"))
        self.resize(1100, 700) # Increased size for sidebar
        self.scraper = BangumiScraper()
        self.initial_query = initial_query
        self._threads = []
        self._current_search_thread = None
        self._current_volume_thread = None
        self._image_loaders = []  # Track image loader threads
        self.field_checkboxes = {}
        self.init_ui()

    def select_all_fields(self):
        for cb in self.field_checkboxes.values():
            cb.setChecked(True)

    def deselect_all_fields(self):
        for cb in self.field_checkboxes.values():
            cb.setChecked(False)

    def get_selected_options(self):
        fields = [k for k, cb in self.field_checkboxes.items() if cb.isChecked()]
        return {
            "fields": fields
        }

    def apply_selection(self, mode):
        if mode == 'series':
            items = self.result_list.selectedItems()
        else:
            items = self.volume_list.selectedItems()
            
        if not items: return
        
        data = items[0].data(Qt.UserRole)
        
        # 如果是从搜索结果页面应用，根据实际类型决定mode
        if mode == 'series':
            # 检查实际类型
            actual_type = data.get("type_label")
            if actual_type == "Volume":
                mode = 'volume'  # 如果实际是Volume，使用volume模式
        
        options = self.get_selected_options()
        self.metadataSelected.emit(data, mode, options)
        self.accept()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        
        # --- Sidebar ---
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("background-color: #18181b; border-right: 1px solid #27272a;")
        sidebar_layout = QVBoxLayout(sidebar)
        
        lbl = QLabel(translator.tr("Scrape Options"))
        lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #e4e4e7; margin-bottom: 10px;")
        sidebar_layout.addWidget(lbl)
        
        # Checkboxes
        self.fields_map = {
            "Title": "Title",
            "Series": "Series",
            "Number": "Number/Volume",
            "Summary": "Summary",
            "Writer": "Writer",
            "Publisher": "Publisher",
            "Date": "Date (Y/M/D)",
            "Genre": "Genre",
            "Tags": "Tags",
            "CommunityRating": "Rating",
            "Status": "Status",
            "ISBN": "ISBN",
            "Format": "Format",
            "Web": "Web URL",
            "Cover": "Cover Image"
        }
        
        # Select All / None
        btn_row = QHBoxLayout()
        all_btn = QPushButton(translator.tr("All"))
        all_btn.clicked.connect(self.select_all_fields)
        none_btn = QPushButton(translator.tr("None"))
        none_btn.clicked.connect(self.deselect_all_fields)
        btn_row.addWidget(all_btn)
        btn_row.addWidget(none_btn)
        sidebar_layout.addLayout(btn_row)
        
        for key, label in self.fields_map.items():
            cb = QCheckBox(translator.tr(label))
            cb.setChecked(True)
            self.field_checkboxes[key] = cb
            sidebar_layout.addWidget(cb)
            
        
        sidebar_layout.addStretch()
        main_layout.addWidget(sidebar)
        
        # --- Main Content ---
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack)
        
        main_layout.addWidget(content_area)
        
        # Page 1: Search
        self.page_search = QWidget()
        self.setup_search_page()
        self.stack.addWidget(self.page_search)
        
        # Page 2: Volumes
        self.page_volumes = QWidget()
        self.setup_volumes_page()
        self.stack.addWidget(self.page_volumes)
        
        if self.initial_query:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, self.start_search)


    def setup_search_page(self):
        layout = QVBoxLayout(self.page_search)
        
        # Search Bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit(self.initial_query)
        self.search_input.setPlaceholderText(translator.tr("Enter series name..."))
        self.search_input.returnPressed.connect(self.start_search)
        
        self.search_btn = QPushButton(translator.tr("Search"))
        self.search_btn.clicked.connect(self.start_search)
        self.search_btn.setProperty("class", "primary")
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        layout.addLayout(search_layout)
        
        # Status Label
        self.search_status = QLabel("")
        self.search_status.setStyleSheet("color: #a1a1aa; font-size: 12px; padding: 5px;")
        self.search_status.hide()
        layout.addWidget(self.search_status)
        
        # Progress
        self.search_progress = QProgressBar()
        self.search_progress.setRange(0, 0)
        self.search_progress.hide()
        layout.addWidget(self.search_progress)
        
        # Results List
        self.result_list = QListWidget()
        self.result_list.setStyleSheet("QListWidget::item { border-bottom: 1px solid #27272a; }")
        self.result_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.result_list.setHorizontalScrollMode(QListWidget.ScrollPerPixel)
        self.result_list.itemSelectionChanged.connect(self.on_search_selection)
        self.result_list.itemDoubleClicked.connect(self.view_volumes)
        layout.addWidget(self.result_list)
        
        # Buttons
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton(translator.tr("Cancel"))
        cancel_btn.clicked.connect(self.reject)
        
        self.view_vols_btn = QPushButton(translator.tr("View Volumes"))
        self.view_vols_btn.clicked.connect(self.view_volumes)
        self.view_vols_btn.setEnabled(False)
        
        self.apply_series_btn = QPushButton(translator.tr("Apply Selected Series"))
        self.apply_series_btn.clicked.connect(lambda: self.apply_selection('series'))
        self.apply_series_btn.setEnabled(False)
        self.apply_series_btn.setProperty("class", "primary")
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self.view_vols_btn)
        btn_layout.addWidget(self.apply_series_btn)
        layout.addLayout(btn_layout)

    def setup_volumes_page(self):
        layout = QVBoxLayout(self.page_volumes)
        
        # Header
        header_layout = QHBoxLayout()
        back_btn = QPushButton(translator.tr("Back to Search"))
        back_btn.clicked.connect(self.back_to_search)
        
        self.series_header_label = QLabel(translator.tr("Series Volumes"))
        self.series_header_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        
        header_layout.addWidget(back_btn)
        header_layout.addWidget(self.series_header_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Content Area
        content_layout = QHBoxLayout()
        
        # Left: Series Info
        series_info_widget = QWidget()
        series_info_widget.setFixedWidth(250)
        series_layout = QVBoxLayout(series_info_widget)
        series_layout.setContentsMargins(0, 0, 10, 0)
        
        self.series_cover_large = QLabel()
        self.series_cover_large.setFixedSize(240, 360)
        self.series_cover_large.setStyleSheet("background-color: #18181b; border: 1px solid #27272a; border-radius: 8px;")
        self.series_cover_large.setScaledContents(True)
        self.series_cover_large.setAlignment(Qt.AlignCenter)
        
        self.series_summary = QTextEdit()
        self.series_summary.setReadOnly(True)
        self.series_summary.setStyleSheet("background-color: transparent; border: none; color: #a1a1aa;")
        
        series_layout.addWidget(self.series_cover_large)
        series_layout.addWidget(self.series_summary)
        
        content_layout.addWidget(series_info_widget)
        
        # Right: Volume List
        right_layout = QVBoxLayout()
        
        # Status Label
        self.vol_status = QLabel("")
        self.vol_status.setStyleSheet("color: #a1a1aa; font-size: 12px; padding: 5px;")
        self.vol_status.hide()
        right_layout.addWidget(self.vol_status)
        
        self.vol_progress = QProgressBar()
        self.vol_progress.setRange(0, 0)
        self.vol_progress.hide()
        right_layout.addWidget(self.vol_progress)
        
        self.volume_list = QListWidget()
        self.volume_list.setStyleSheet("""
            QListWidget { background-color: #18181b; border: 1px solid #27272a; border-radius: 4px; }
            QListWidget::item { border-bottom: 1px solid #27272a; padding: 5px; }
            QListWidget::item:selected { background-color: #27272a; }
        """)
        self.volume_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.volume_list.setHorizontalScrollMode(QListWidget.ScrollPerPixel)
        self.volume_list.itemSelectionChanged.connect(self.on_volume_selection)
        right_layout.addWidget(self.volume_list)
        
        content_layout.addLayout(right_layout)
        layout.addLayout(content_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.apply_vol_btn = QPushButton(translator.tr("Apply Selected Volume"))
        self.apply_vol_btn.clicked.connect(lambda: self.apply_selection('volume'))
        self.apply_vol_btn.setEnabled(False)
        self.apply_vol_btn.setProperty("class", "primary")
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.apply_vol_btn)
        layout.addLayout(btn_layout)

    def start_search(self):
        query = self.search_input.text().strip()
        if not query:
            return
        
        # Cancel any running search thread
        if self._current_search_thread and self._current_search_thread.isRunning():
            self._current_search_thread.cancel()
            self._current_search_thread.wait(1000)  # Wait up to 1 second
            if self._current_search_thread.isRunning():
                self._current_search_thread.terminate()
                self._current_search_thread.wait()
        
        self.search_status.setText(translator.tr("Preparing search..."))
        self.search_status.show()
        self.search_progress.show()
        self.result_list.clear()
        self.apply_series_btn.setEnabled(False)
        self.view_vols_btn.setEnabled(False)
        self.search_btn.setEnabled(False)  # Disable search button
        
        thread = SearchThread(self.scraper, query)
        thread.resultsReady.connect(self.on_search_results)
        thread.errorOccurred.connect(self.on_error)
        thread.statusUpdate.connect(self.on_search_status)
        thread.finished.connect(lambda: self.on_search_finished(thread))
        self._threads.append(thread)
        self._current_search_thread = thread
        thread.start()

    def on_search_status(self, status):
        self.search_status.setText(status)
    
    def on_search_finished(self, thread):
        """Called when search thread finishes"""
        self.search_btn.setEnabled(True)  # Re-enable search button
        self.cleanup_thread(thread)
        if thread == self._current_search_thread:
            self._current_search_thread = None

    def on_search_results(self, results):
        self.search_progress.hide()
        self.search_status.hide()
        if not results:
            QMessageBox.information(self, translator.tr("No Results"), translator.tr("No matches found. Try a different search term."))
            return
            
        for res in results:
            item = QListWidgetItem(self.result_list)
            item.setSizeHint(QSize(0, 110))  # 增加高度以容纳更多信息
            item.setData(Qt.UserRole, res)
            widget = ResultItemWidget(res)
            self.result_list.setItemWidget(item, widget)
            # Track image loader if it exists
            if widget.image_loader:
                self._image_loaders.append(widget.image_loader)

    def on_search_selection(self):
        items = self.result_list.selectedItems()
        if not items:
            self.apply_series_btn.setEnabled(False)
            self.view_vols_btn.setEnabled(False)
            return
            
        data = items[0].data(Qt.UserRole)
        is_series = data.get("type_label") == "Series"
        
        # 根据类型调整按钮
        self.apply_series_btn.setEnabled(True)
        if is_series:
            self.apply_series_btn.setText(translator.tr("Apply Selected Series"))
            self.view_vols_btn.setEnabled(True)
        else:
            self.apply_series_btn.setText(translator.tr("Apply Selected Volume"))
            self.view_vols_btn.setEnabled(False)

    def view_volumes(self):
        items = self.result_list.selectedItems()
        if not items: return
        
        data = items[0].data(Qt.UserRole)
        if data.get("type_label") != "Series":
            return
            
        self.current_series = data
        self.series_header_label.setText(f"Volumes: {data.get('name_cn') or data.get('name')}")
        self.series_summary.setText(data.get("summary", translator.tr("No summary available.")))
        
        # Load large cover
        images = data.get("images") or data.get("image")
        if images and isinstance(images, dict):
            url = images.get("large") or images.get("common")
            if url:
                if url.startswith("//"): url = "https:" + url
                self.loader = ImageLoader(url)
                self.loader.imageLoaded.connect(lambda p: self.series_cover_large.setPixmap(p.scaled(self.series_cover_large.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)))
                self.loader.start()
        else:
            self.series_cover_large.setText("No Cover")
        
        # Cancel any running volume thread
        if self._current_volume_thread and self._current_volume_thread.isRunning():
            self._current_volume_thread.cancel()
            self._current_volume_thread.wait(1000)
            if self._current_volume_thread.isRunning():
                self._current_volume_thread.terminate()
                self._current_volume_thread.wait()
        
        self.stack.setCurrentWidget(self.page_volumes)
        self.volume_list.clear()
        self.vol_status.setText(translator.tr("Loading volumes..."))
        self.vol_status.show()
        self.vol_progress.show()
        
        thread = VolumeThread(self.scraper, data['id'])
        thread.volumesReady.connect(self.on_volumes_ready)
        thread.errorOccurred.connect(self.on_error)
        thread.statusUpdate.connect(self.on_volume_status)
        thread.finished.connect(lambda: self.on_volume_finished(thread))
        self._threads.append(thread)
        self._current_volume_thread = thread
        thread.start()

    def on_volume_status(self, status):
        self.vol_status.setText(status)
    
    def on_volume_finished(self, thread):
        """Called when volume thread finishes"""
        self.cleanup_thread(thread)
        if thread == self._current_volume_thread:
            self._current_volume_thread = None

    def on_volumes_ready(self, volumes):
        self.vol_progress.hide()
        self.vol_status.hide()
        if not volumes:
            self.vol_status.setText("No volumes found for this series.")
            self.vol_status.show()
            return
            
        for vol in volumes:
            item = QListWidgetItem(self.volume_list)
            item.setSizeHint(QSize(0, 110))  # 增加高度以容纳更多信息
            item.setData(Qt.UserRole, vol)
            widget = ResultItemWidget(vol)
            self.volume_list.setItemWidget(item, widget)
            # Track image loader if it exists
            if widget.image_loader:
                self._image_loaders.append(widget.image_loader)

    def on_volume_selection(self):
        items = self.volume_list.selectedItems()
        self.apply_vol_btn.setEnabled(len(items) > 0)

    def back_to_search(self):
        self.stack.setCurrentWidget(self.page_search)


    def on_error(self, msg):
        self.search_progress.hide()
        self.search_status.hide()
        self.vol_progress.hide()
        self.vol_status.hide()
        
        # Show detailed error message
        error_dialog = QMessageBox(self)
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setWindowTitle("Network Error")
        error_dialog.setText("An error occurred while communicating with Bangumi API.")
        error_dialog.setInformativeText(msg)
        error_dialog.setDetailedText(
            "Troubleshooting tips:\n"
            "1. Check your internet connection\n"
            "2. Verify that api.bgm.tv is accessible\n"
            "3. Try again in a few moments\n"
            "4. If the problem persists, the API may be temporarily unavailable"
        )
        error_dialog.exec()

    def cleanup_thread(self, thread):
        if thread in self._threads:
            self._threads.remove(thread)
        # Don't delete immediately, let Qt handle it
        thread.deleteLater()

    def closeEvent(self, event):
        """Properly clean up all threads before closing"""
        # Cancel all image loaders first
        for loader in self._image_loaders[:]:
            try:
                if loader and loader.isRunning():
                    if hasattr(loader, 'cancel'):
                        loader.cancel()
                    loader.wait(500)  # Wait briefly
                    if loader.isRunning():
                        loader.terminate()
            except RuntimeError:
                # C++ object already deleted
                continue
        
        # Cancel and wait for all main threads to finish
        for t in self._threads[:]:
            if t.isRunning():
                # Cancel thread if it has the method
                if hasattr(t, 'cancel'):
                    t.cancel()
                # Wait for thread to finish
                t.wait(2000)  # Wait up to 2 seconds
                if t.isRunning():
                    # Force terminate if still running
                    t.terminate()
                    t.wait()
        super().closeEvent(event)
