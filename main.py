import sys
import os
import traceback

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon
from ui.main_window import MainWindow
from utils.logger import logger

def exception_hook(exctype, value, tb):
    """Global exception handler."""
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    logger.critical(f"Uncaught exception:\n{error_msg}")
    
    # Ensure QApplication exists before showing message box
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    # Show error dialog
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle("Critical Error")
    msg.setText("An unexpected error occurred.")
    msg.setDetailedText(error_msg)
    msg.exec()
    
    # Call original hook
    sys.__excepthook__(exctype, value, tb)
    sys.exit(1)

def main():
    # Set global exception hook
    sys.excepthook = exception_hook
    
    logger.info("Application starting...")
    
    app = QApplication(sys.argv)
    app.setApplicationName("ComicMeta Editor")
    app.setOrganizationName("DAZAO")
    
    # Set application icon
    # 支持打包后的路径（PyInstaller）
    if getattr(sys, 'frozen', False):
        # 运行在打包的 exe 中
        base_path = sys._MEIPASS
    else:
        # 运行在普通 Python 环境中
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    icon_path = os.path.join(base_path, "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = MainWindow()
    window.show()
    
    exit_code = app.exec()
    logger.info(f"Application exiting with code {exit_code}")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
