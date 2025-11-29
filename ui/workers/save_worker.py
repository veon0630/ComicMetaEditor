from PySide6.QtCore import QObject, Signal, QRunnable, Slot, QThreadPool
import time
from config import Config
from utils.logger import logger

class SaveWorkerSignals(QObject):
    """Signals for the SaveRunnable."""
    finished = Signal(object) # ComicFile (success)
    error = Signal(object, str) # ComicFile, error message
    file_progress = Signal(object, int) # ComicFile, percent (0-100)

class SaveRunnable(QRunnable):
    """Runnable for saving a single file."""
    def __init__(self, comic_file):
        super().__init__()
        self.comic_file = comic_file
        self.signals = SaveWorkerSignals()

    @Slot()
    def run(self):
        try:
            def progress_callback(percent):
                self.signals.file_progress.emit(self.comic_file, percent)
                
            self.comic_file.save(progress_callback=progress_callback)
            self.signals.finished.emit(self.comic_file)
        except Exception as e:
            self.signals.error.emit(self.comic_file, str(e))

class BatchSaveManager(QObject):
    """Manages the batch saving process using QThreadPool."""
    progress_updated = Signal(int, int) # current, total
    file_completed = Signal(object) # ComicFile
    file_failed = Signal(object, str) # ComicFile, error
    all_finished = Signal()
    
    def __init__(self, files_to_save):
        super().__init__()
        self.files = files_to_save
        self.total = len(files_to_save)
        self.completed_count = 0
        self.failed_count = 0
        self.is_cancelled = False
        self.thread_pool = QThreadPool()
        
        # Track progress of each file (0-100)
        self.file_progress_map = {f: 0 for f in files_to_save}
        
        # Progress throttling to prevent UI freezing
        self._last_progress_time = 0
        self._progress_throttle = Config.PROGRESS_UPDATE_THROTTLE

    def start(self):
        if not self.files:
            self.all_finished.emit()
            return

        for cf in self.files:
            worker = SaveRunnable(cf)
            worker.signals.finished.connect(self.on_worker_finished)
            worker.signals.error.connect(self.on_worker_error)
            worker.signals.file_progress.connect(self.on_worker_file_progress)
            self.thread_pool.start(worker)

    def cancel(self):
        self.is_cancelled = True
        self.thread_pool.clear() # Remove queued tasks
        # Cannot stop running tasks easily in QThreadPool

    def on_worker_file_progress(self, comic_file, percent):
        if self.is_cancelled: return
        self.file_progress_map[comic_file] = percent
        self._emit_aggregate_progress()

    def on_worker_finished(self, comic_file):
        if self.is_cancelled: return
        self.completed_count += 1
        self.file_progress_map[comic_file] = 100
        self.file_completed.emit(comic_file)
        self._emit_aggregate_progress(force=True)
        self._check_finished()

    def on_worker_error(self, comic_file, error_msg):
        if self.is_cancelled: return
        logger.error(f"Error saving {comic_file.file_path}: {error_msg}")
        self.failed_count += 1
        self.file_progress_map[comic_file] = 100 # Treat failed as done for progress
        self.file_failed.emit(comic_file, error_msg)
        self._emit_aggregate_progress(force=True)
        self._check_finished()

    def _check_finished(self):
        if self.completed_count + self.failed_count >= self.total:
            self.all_finished.emit()

    def _emit_aggregate_progress(self, force=False):
        """Calculate total progress across all files and emit."""
        current_time = time.time()
        if not force and (current_time - self._last_progress_time < self._progress_throttle):
            return
            
        self._last_progress_time = current_time
        
        # Calculate total progress (0 to 100 * total)
        total_progress_points = sum(self.file_progress_map.values())
        # Scale to 0-10000 for progress bar (allows for float precision)
        max_points = self.total * 100
        if max_points == 0:
            scaled_progress = 0
        else:
            scaled_progress = int((total_progress_points / max_points) * 10000)
            
        self.progress_updated.emit(scaled_progress, 10000)
