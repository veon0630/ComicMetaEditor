from PySide6.QtCore import QThread, Signal
from core.command_manager import CommandManager
from core.scraper import BangumiScraper

class BatchScrapeWorker(QThread):
    """
    Worker thread for batch scraping operations.
    Prevents UI freezing during long API waits (rate limiting).
    """
    progress_updated = Signal(int, int)  # current, total
    finished = Signal(int, list)         # success_count, failed_list
    error_occurred = Signal(str)         # error message

    def __init__(self, files, indexes, bangumi_data, mode, options, access_token=None):
        super().__init__()
        self.files = files
        self.indexes = indexes
        self.bangumi_data = bangumi_data
        self.mode = mode
        self.options = options
        self.scraper = BangumiScraper(access_token=access_token)
        self._is_cancelled = False


    def run(self):
        try:
            total = len(self.indexes)
            
            def progress_callback(current_idx):
                if self._is_cancelled:
                    return True
                self.progress_updated.emit(current_idx + 1, total)
                return False

            success_count, failed_list = CommandManager.apply_scraped_data(
                self.files, 
                self.indexes, 
                self.bangumi_data, 
                self.mode, 
                self.options, 
                self.scraper, 
                progress_callback
            )
            
            if not self._is_cancelled:
                self.finished.emit(success_count, failed_list)
                
        except Exception as e:
            self.error_occurred.emit(str(e))

    def cancel(self):
        self._is_cancelled = True
