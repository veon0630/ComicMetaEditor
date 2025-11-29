from PySide6.QtCore import QThread, Signal
from pathlib import Path
from core.file_loader import FileLoader
from utils.logger import logger

class FileLoaderWorker(QThread):
    """
    Worker thread for loading files asynchronously.
    Emits signals for progress and completion.
    """
    progress = Signal(int, int)  # current, total
    file_loaded = Signal(object) # ComicFile
    finished_loading = Signal(list) # list[ComicFile]
    error_occurred = Signal(str)

    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = Path(folder_path)
        self.is_cancelled = False

    def run(self):
        try:
            # 1. Scan files
            paths = FileLoader.scan_directory(self.folder_path)
        except Exception as e:
            self.error_occurred.emit(str(e))
            return

        if not paths:
            self.finished_loading.emit([])
            return

        total = len(paths)
        loaded_files = []

        # 2. Load each file
        for i, path in enumerate(paths):
            if self.is_cancelled:
                break
            
            try:
                cf = FileLoader.load_file(path)
                loaded_files.append(cf)
                self.file_loaded.emit(cf)
            except Exception as e:
                # Logged in FileLoader, just continue
                pass
            
            self.progress.emit(i + 1, total)

        self.finished_loading.emit(loaded_files)

    def cancel(self):
        self.is_cancelled = True
