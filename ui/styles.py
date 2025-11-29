class Styles:
    DARK_THEME = """
    QMainWindow, QDialog {
        background-color: #1e1e1e;
        color: #ffffff;
    }
    QWidget {
        background-color: #1e1e1e;
        color: #ffffff;
        font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    }
    
    /* Main Workspace Container */
    #workspaceContainer {
        border: 1px solid #3e3e42;
        border-radius: 8px;
        margin: 5px;
        background-color: #1e1e1e;
    }
    
    /* Toolbar */
    QToolBar {
        background-color: #252526;
        border: none;
        padding: 2px;
        spacing: 4px;
    }
    QToolBar::separator {
        background-color: #4CAF50;
        width: 1px;
        margin: 2px 4px;
    }
    QToolButton {
        background-color: #2d2d2d;
        border: 1px solid #3e3e42;
        border-radius: 3px;
        padding: 2px 8px;
        color: #cccccc;
        font-size: 9pt;
        text-transform: uppercase;
    }
    QToolButton:hover {
        background-color: #3e3e42;
        border: 1px solid #4CAF50;
        color: #ffffff;
    }
    QToolButton:pressed {
        background-color: #4CAF50;
        border: 1px solid #45a049;
        color: #ffffff;
    }
    
    /* Menu Bar */
    QMenuBar {
        background-color: #252526;
        border-bottom: 1px solid #3e3e42;
        padding: 2px;
    }
    QMenuBar::item {
        background-color: transparent;
        padding: 4px 8px;
        color: #cccccc;
    }
    QMenuBar::item:selected {
        background-color: #2d2d2d;
        border: 1px solid #4CAF50;
        color: #ffffff;
    }
    QMenuBar::item:pressed {
        background-color: #4CAF50;
    }
    
    /* Menu (Dropdown & Context Menu) */
    QMenu {
        background-color: #252526;
        border: 1px solid #3e3e42;
        padding: 4px 0px;
    }
    QMenu::item {
        background-color: transparent;
        padding: 6px 30px 6px 20px;
        color: #cccccc;
    }
    QMenu::item:selected {
        background-color: #2d2d2d;
        color: #4CAF50;
    }
    QMenu::separator {
        height: 1px;
        background-color: #3e3e42;
        margin: 4px 8px;
    }
    QMenu::indicator {
        width: 13px;
        height: 13px;
        margin-left: 5px;
    }
    
    /* Splitter */
    QSplitter::handle {
        background-color: #3e3e42;
    }
    
    /* Table View */
    QTableView {
        background-color: #1e1e1e;
        gridline-color: #3e3e42;
        border: none;
        selection-background-color: #2d2d2d;
        selection-color: #4CAF50;
    }
    QHeaderView::section {
        background-color: #252526;
        color: #cccccc;
        padding: 6px;
        border: none;
        border-bottom: 1px solid #3e3e42;
        border-right: 1px solid #3e3e42;
        font-weight: bold;
    }
    QTableView::item {
        padding: 5px;
        border-bottom: 1px solid #2d2d2d;
    }
    QTableView::item:selected {
        background-color: #2d2d2d;
        color: #4CAF50;
    }
    
    /* Buttons */
    QPushButton {
        background-color: #2d2d2d;
        border: 1px solid #3e3e42;
        border-radius: 4px;
        padding: 6px 12px;
        color: #ffffff;
    }
    QPushButton:hover {
        background-color: #3e3e42;
        border-color: #4CAF50;
    }
    QPushButton:pressed {
        background-color: #1e1e1e;
    }
    QPushButton:disabled {
        background-color: #1e1e1e;
        color: #555555;
        border-color: #2d2d2d;
    }
    
    /* Primary Button (Green) */
    QPushButton[class="primary"] {
        background-color: #4CAF50;
        border: none;
        color: white;
        font-weight: bold;
    }
    QPushButton[class="primary"]:hover {
        background-color: #45a049;
    }
    
    /* Inputs */
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox {
        background-color: #252526;
        border: 1px solid #3e3e42;
        border-radius: 4px;
        padding: 4px;
        color: #ffffff;
    }
    QLineEdit:focus, QTextEdit:focus {
        border: 1px solid #4CAF50;
    }

    /* ComboBox */
    QComboBox {
        background-color: #252526;
        border: 1px solid #3e3e42;
        border-radius: 4px;
        padding: 4px;
        color: #ffffff;
    }
    QComboBox:hover {
        border: 1px solid #4CAF50;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 20px;
        border-left-width: 0px;
        border-top-right-radius: 4px;
        border-bottom-right-radius: 4px;
        background: transparent;
    }
    
    /* Scrollbar */
    QScrollBar:vertical {
        border: none;
        background: #1e1e1e;
        width: 10px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background: #424242;
        min-height: 20px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical:hover {
        background: #4CAF50;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
    }
    /* Horizontal */
    QScrollBar:horizontal {
        border: none;
        background: #1e1e1e;
        height: 10px;
        margin: 0px;
    }
    QScrollBar::handle:horizontal {
        background: #424242;
        min-width: 20px;
        border-radius: 5px;
    }
    QScrollBar::handle:horizontal:hover {
        background: #4CAF50;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
        background: none;
    }

    /* Tab Widget */
    QTabWidget::pane {
        border: 1px solid #3e3e42;
        background: #1e1e1e;
    }
    QTabBar::tab {
        background: #252526;
        color: #cccccc;
        padding: 8px 16px;
        border: 1px solid #3e3e42;
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        margin-right: 2px;
    }
    QTabBar::tab:selected {
        background: #1e1e1e;
        color: #4CAF50;
        border-top: 2px solid #4CAF50;
    }
    
    /* Group Box */
    QGroupBox {
        color: #ffffff;
        border: 1px solid #3e3e42;
        border-radius: 5px;
        margin-top: 20px;
        padding-top: 20px;
        font-weight: bold;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
        color: #4CAF50;
    }
    
    /* Labels */
    QLabel {
        color: #cccccc;
    }
    QLabel[class="header"] {
        font-size: 16px;
        font-weight: bold;
        color: #4CAF50;
        margin-top: 10px;
        margin-bottom: 5px;
    }
    """
