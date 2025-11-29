import os
import sys
from pathlib import Path
import time

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QSplitter, QToolBar, QFileDialog, QMessageBox, 
                               QStatusBar, QLabel, QProgressDialog, QApplication,
                               QDialog, QListWidget, QDialogButtonBox, QInputDialog)
from PySide6.QtGui import QAction, QIcon, QKeySequence, QActionGroup
from PySide6.QtCore import Qt, QSize, QItemSelectionModel, QThread, Signal

from core.comic_file import ComicFile
from core.command_manager import CommandManager
from ui.file_table import FileTable, ComicTableModel
from ui.editor_panel import EditorPanel
from ui.scraper_dialog import ScraperDialog
from ui.styles import Styles
from ui.workers.loader_worker import FileLoaderWorker
from ui.workers.save_worker import BatchSaveManager
from core.translator import translator
from config import Config
from utils.logger import logger

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ComicMeta Editor")
        self.resize(1400, 800)
        self.setStyleSheet(Styles.DARK_THEME)
        
        # Set window icon
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = Path(__file__).parent.parent
        
        icon_path = Path(base_path) / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        self.files = []
        self.current_dir = None
        self.loader_worker = None
        self.save_manager = None
        self.failed_files = []
        
        self.init_ui()
        
        # Connect language change signal
        translator.languageChanged.connect(self.retranslate_ui)
        self.retranslate_ui()
        
    def init_ui(self):
        # Menu Bar
        menubar = self.menuBar()
        
        # File Menu
        self.file_menu = menubar.addMenu("File")
        
        self.open_act = QAction("Open Folder", self)
        self.open_act.setShortcut("Ctrl+O")
        self.open_act.triggered.connect(self.open_folder)
        self.file_menu.addAction(self.open_act)
        
        self.file_menu.addSeparator()
        
        self.save_act = QAction("Save All", self)
        self.save_act.setShortcut("Ctrl+S")
        self.save_act.triggered.connect(self.save_all)
        self.file_menu.addAction(self.save_act)
        
        self.save_sel_act = QAction("Save Selected", self)
        self.save_sel_act.setShortcut("Ctrl+Shift+S")
        self.save_sel_act.triggered.connect(self.save_selected)
        self.file_menu.addAction(self.save_sel_act)
        
        self.file_menu.addSeparator()
        
        self.exit_act = QAction("Exit", self)
        self.exit_act.triggered.connect(self.close)
        self.file_menu.addAction(self.exit_act)
        
        # Select Menu
        self.select_menu = menubar.addMenu("Select")
        
        self.select_all_act = QAction("Select All", self)
        self.select_all_act.setShortcut("Ctrl+A")
        self.select_all_act.triggered.connect(self.select_all)
        self.select_menu.addAction(self.select_all_act)
        
        self.deselect_act = QAction("Deselect", self)
        self.deselect_act.setShortcut("Ctrl+D")
        self.deselect_act.triggered.connect(self.deselect_all)
        self.select_menu.addAction(self.deselect_act)
        
        self.invert_act = QAction("Invert Selection", self)
        self.invert_act.setShortcut("Ctrl+I")
        self.invert_act.triggered.connect(self.invert_selection)
        self.select_menu.addAction(self.invert_act)
        
        # Tools Menu
        self.tools_menu = menubar.addMenu("Tools")
        
        self.scrape_act = QAction("Scrape", self)
        self.scrape_act.setShortcut("Ctrl+F")
        self.scrape_act.triggered.connect(self.open_scraper)
        self.tools_menu.addAction(self.scrape_act)
        
        self.autonum_act = QAction("Auto Number", self)
        self.autonum_act.triggered.connect(self.auto_number)
        self.tools_menu.addAction(self.autonum_act)
        
        self.convert_act = QAction("Convert Format", self)
        self.convert_act.triggered.connect(self.convert_format)
        self.tools_menu.addAction(self.convert_act)
        
        # Settings Menu
        self.settings_menu = menubar.addMenu("Settings")
        
        self.columns_act = QAction("Customize Columns", self)
        self.columns_act.triggered.connect(self.show_column_settings)
        self.settings_menu.addAction(self.columns_act)
        
        # Language Submenu
        self.lang_menu = self.settings_menu.addMenu(translator.tr("Language"))
        
        lang_group = QActionGroup(self)
        
        # Define display names for languages
        lang_data = translator.get_languages_with_names()
        current_lang = translator.get_current_language()
        
        for lang_code, display_name in lang_data.items():
            action = QAction(display_name, self, checkable=True)
            action.setData(lang_code) # Store language code in action data
            action.triggered.connect(lambda checked, code=lang_code: translator.set_language(code))
            lang_group.addAction(action)
            self.lang_menu.addAction(action)
            
            if lang_code == current_lang:
                action.setChecked(True)
        
        # Help Menu
        self.help_menu = menubar.addMenu("Help")
        
        self.guide_act = QAction("Usage Guide", self)
        self.guide_act.triggered.connect(self.show_help)
        self.help_menu.addAction(self.guide_act)
        
        self.about_act = QAction("About", self)
        self.about_act.triggered.connect(self.show_about)
        self.help_menu.addAction(self.about_act)
        
        self.help_menu.addSeparator()
        
        self.update_act = QAction("Check for Updates", self)
        self.update_act.triggered.connect(self.check_for_updates)
        self.help_menu.addAction(self.update_act)

        # Toolbar
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Toolbar Actions
        toolbar.addAction(self.open_act)
        toolbar.addAction(self.save_act)
        toolbar.addAction(self.save_sel_act)
        
        toolbar.addSeparator()
        
        toolbar.addAction(self.scrape_act)
        toolbar.addAction(self.autonum_act)
        toolbar.addAction(self.convert_act)
        
        # Central Widget
        splitter = QSplitter(Qt.Horizontal)
        
        # Left: Table
        self.table = FileTable()
        self.model = ComicTableModel()
        self.table.setModel(self.model)
        self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)
        splitter.addWidget(self.table)
        
        # Right: Editor
        self.editor = EditorPanel()
        self.editor.metadataChanged.connect(self.on_metadata_changed)
        splitter.addWidget(self.editor)
        
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        
        self.setCentralWidget(splitter)
        
        # Status Bar
        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        self.status_bar.setStyleSheet("QStatusBar::item { border: none; }")
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)
        
        # Version label
        from core._version import __version__
        version_label = QLabel(f"Ver.{__version__}")
        version_label.setStyleSheet("color: #71717a; font-size: 11px; margin-right: 10px;")
        self.status_bar.addPermanentWidget(version_label)

    def retranslate_ui(self):
        """Update UI texts based on current language."""
        self.setWindowTitle(translator.tr("ComicMeta Editor"))
        
        # Menus
        self.file_menu.setTitle(translator.tr("File"))
        self.select_menu.setTitle(translator.tr("Select"))
        self.tools_menu.setTitle(translator.tr("Tools"))
        self.settings_menu.setTitle(translator.tr("Settings"))
        self.help_menu.setTitle(translator.tr("Help"))
        self.lang_menu.setTitle(translator.tr("Language"))
        
        # Actions
        self.open_act.setText(translator.tr("Open Folder"))
        self.save_act.setText(translator.tr("Save All"))
        self.save_sel_act.setText(translator.tr("Save Selected"))
        self.exit_act.setText(translator.tr("Exit"))
        
        self.select_all_act.setText(translator.tr("Select All"))
        self.deselect_act.setText(translator.tr("Deselect"))
        self.invert_act.setText(translator.tr("Invert Selection"))
        
        self.scrape_act.setText(translator.tr("Scrape"))
        self.autonum_act.setText(translator.tr("Auto Number"))
        self.convert_act.setText(translator.tr("Convert Format"))
        
        self.columns_act.setText(translator.tr("Customize Columns"))
        
        self.guide_act.setText(translator.tr("Usage Guide"))
        self.about_act.setText(translator.tr("About"))
        self.update_act.setText(translator.tr("Check for Updates"))
        
        self.status_label.setText(translator.tr("Ready"))
        
        if hasattr(self, 'model'):
            self.model.refresh_headers()
            
        if hasattr(self, 'editor'):
            self.editor.retranslate_ui()

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, translator.tr("Select Folder"))
        if not folder:
            return
        
        logger.info(f"User opened folder: {folder}")
        self.current_dir = Path(folder)
        self.load_files(self.current_dir)

    def load_files(self, folder):
        logger.info(f"Loading files from: {folder}")
        self.files = []
        self.model.update_files([])
        
        self.loader_worker = FileLoaderWorker(folder)
        
        self.progress_dialog = QProgressDialog(translator.tr("Loading files..."), "Cancel", 0, 100, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.canceled.connect(self.loader_worker.cancel)
        
        self.loader_worker.progress.connect(self.on_load_progress)
        self.loader_worker.finished_loading.connect(self.on_load_finished)
        self.loader_worker.error_occurred.connect(self.on_load_error)
        
        self.loader_worker.start()

    def on_load_progress(self, current, total):
        self.progress_dialog.setMaximum(total)
        self.progress_dialog.setValue(current)
        self.status_label.setText(translator.tr("Loading... {}/{}").format(current, total))

    def on_load_finished(self, loaded_files):
        self.files = loaded_files
        self.model.update_files(self.files)
        logger.info(f"Successfully loaded {len(self.files)} comic files")
        self.status_label.setText(translator.tr("Loaded {} files").format(len(self.files)))
        self.progress_dialog.close()
        
        if not self.files and self.current_dir:
             QMessageBox.warning(self, translator.tr("No Files Found"), translator.tr("No .zip or .cbz files found in the selected folder."))

    def on_load_error(self, error_msg):
        self.progress_dialog.close()
        QMessageBox.critical(self, translator.tr("Error"), translator.tr("Failed to access folder: {}").format(error_msg))

    def on_selection_changed(self):
        indexes = self.table.selectionModel().selectedRows()
        selected_files = [self.files[i.row()] for i in indexes]
        self.editor.load_selection(selected_files)
        self.status_label.setText(translator.tr("Selected {} files").format(len(selected_files)))

    def on_metadata_changed(self, key, value):
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return
        
        logger.info(f"User modified metadata: {key} = {value} (affecting {len(indexes)} files)")
        for i in indexes:
            file_obj = self.files[i.row()]
            file_obj.set_metadata(key, value)
            self.model.refresh_row(i.row())

    def open_scraper(self):
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            indexes = [self.model.index(i, 0) for i in range(len(self.files))]
        
        logger.info(f"User opened scraper for {len(indexes)} files")
        if not indexes:
            QMessageBox.warning(self, translator.tr("Warning"), translator.tr("No files to scrape."))
            return
            
        first_file = self.files[indexes[0].row()]
        query = first_file.get_metadata("Series") or first_file.get_metadata("Title") or first_file.file_path.stem
        
        dialog = ScraperDialog(self, initial_query=query)
        dialog.metadataSelected.connect(lambda data, mode, options: self.apply_scrape_result(data, mode, indexes, options))
        dialog.exec()

    def apply_scrape_result(self, bangumi_data, mode, indexes, options):
        logger.info(f"Applying scraped metadata (mode={mode}) to {len(indexes)} files")
        
        from core.scraper import BangumiScraper
        scraper = BangumiScraper()
        
        progress = QProgressDialog(translator.tr("Applying metadata..."), "Cancel", 0, len(indexes), self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        QApplication.processEvents()

        try:
            def progress_callback(current_idx):
                if progress.wasCanceled():
                    return True # Cancelled
                progress.setValue(current_idx + 1)
                return False

            count = CommandManager.apply_scraped_data(
                self.files, indexes, bangumi_data, mode, options, scraper, progress_callback
            )
            
            # Refresh UI
            for idx in indexes:
                self.model.refresh_row(idx.row())
                
            QMessageBox.information(self, translator.tr("Success"), translator.tr("Applied metadata to {} files.").format(count))
            logger.info(f"Successfully applied scraped metadata to {count} files")
            self.on_selection_changed()
            
        except Exception as e:
            QMessageBox.critical(self, translator.tr("Error"), translator.tr("Failed to apply metadata: {}").format(e))
        finally:
            progress.close()

    def auto_number(self):
        if not self.files:
            QMessageBox.warning(self, translator.tr("Warning"), translator.tr("No files loaded. Please open a folder first."))
            return

        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            indexes = [self.model.index(i, 0) for i in range(len(self.files))]
        
        logger.info(f"User triggered auto-numbering for {len(indexes)} files")
        if not indexes:
            return
            
        # Delegate to CommandManager
        modified_files = CommandManager.auto_number(self.files, indexes)
        
        # Refresh UI for modified rows
        for idx in indexes:
            self.model.refresh_row(idx.row())
        
        logger.info(f"Auto-numbering completed for {len(modified_files)} files")
        self.on_selection_changed()

    def convert_format(self):
        if not self.files:
            QMessageBox.warning(self, translator.tr("Warning"), translator.tr("No files loaded. Please open a folder first."))
            return

        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            indexes = [self.model.index(i, 0) for i in range(len(self.files))]
        
        logger.info(f"User initiated format conversion for {len(indexes)} files")
        
        items = [".cbz (Comic Book Archive)", ".zip (Standard Archive)"]
        item, ok = QInputDialog.getItem(self, translator.tr("Convert Format"), translator.tr("Convert to:"), items, 0, False)
        
        if not ok or not item:
            return
            
        target_ext = '.cbz' if '.cbz' in item else '.zip'
        
        success_count, failed_list = CommandManager.convert_format(self.files, indexes, target_ext)
        
        # Refresh all because filenames changed (even if failed, some might have succeeded)
        for idx in indexes:
            self.model.refresh_row(idx.row())
            
        if failed_list:
            error_lines = [f"{name}: {err}" for name, err in failed_list]
            error_text = "\n".join(error_lines)
            
            msg = translator.tr("Conversion completed with errors.") + "\n\n" \
                  f"{translator.tr('Success')}: {success_count}\n" \
                  f"{translator.tr('Failed')}: {len(failed_list)}\n\n" \
                  f"{translator.tr('Failed files:')}\n{error_text}"
                  
            QMessageBox.warning(self, translator.tr("Conversion Errors"), msg)
            logger.warning(f"Format conversion finished with errors: {success_count} success, {len(failed_list)} failed")
        
        elif success_count > 0:
            logger.info(f"Format conversion completed: {success_count} files converted to {target_ext}")
            QMessageBox.information(self, translator.tr("Success"), translator.tr("Converted {} file(s) to {}").format(success_count, target_ext))
        else:
            QMessageBox.information(self, translator.tr("Info"), translator.tr("No files needed conversion."))
            
        self.on_selection_changed()

    def confirm_save(self, files_to_save):
        dialog = QDialog(self)
        dialog.setWindowTitle(translator.tr("Confirm Save"))
        dialog.resize(500, 400)
        
        layout = QVBoxLayout(dialog)
        label = QLabel(translator.tr("The following {} files will be saved:").format(len(files_to_save)))
        layout.addWidget(label)
        
        list_widget = QListWidget()
        for f in files_to_save:
            list_widget.addItem(f.file_path.name)
        layout.addWidget(list_widget)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        return dialog.exec() == QDialog.Accepted

    def start_batch_save(self, files_to_save):
        logger.info(f"Starting batch save for {len(files_to_save)} files")
        self.save_manager = BatchSaveManager(files_to_save)
        
        self.progress_dialog = QProgressDialog(translator.tr("Saving files..."), "Cancel", 0, 10000, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.canceled.connect(self.save_manager.cancel)
        
        self.save_manager.progress_updated.connect(self.on_save_progress)
        self.save_manager.file_completed.connect(self.on_file_saved)
        self.save_manager.file_failed.connect(self.on_file_failed)
        self.save_manager.all_finished.connect(self.on_save_finished)
        
        self.save_manager.start()

    def on_save_progress(self, current, total):
        self.progress_dialog.setMaximum(total)
        self.progress_dialog.setValue(current)
        percent = (current / total) * 100 if total > 0 else 0
        self.status_label.setText(translator.tr("Saving... {:.1f}%").format(percent))

    def on_file_saved(self, comic_file):
        try:
            row = self.files.index(comic_file)
            self.model.refresh_row(row)
        except ValueError:
            pass

    def on_file_failed(self, comic_file, error_msg):
        self.failed_files.append((comic_file, error_msg))
        try:
            row = self.files.index(comic_file)
            self.model.refresh_row(row)
        except ValueError:
            pass

    def on_save_finished(self):
        self.progress_dialog.close()
        total = self.save_manager.total
        success = self.save_manager.completed_count
        
        if self.failed_files:
            error_lines = [f"{f.file_path.name}: {e}" for f, e in self.failed_files]
            error_text = "\n".join(error_lines)
            QMessageBox.warning(self, translator.tr("Save Complete with Errors"),
                                translator.tr("Saved {}/{} files.").format(success, total) + f"\n\n{translator.tr('Failed files:')}\n{error_text}")
            logger.warning(f"Batch save completed with errors: {success}/{total} successful")
        else:
            QMessageBox.information(self, translator.tr("Save Complete"), translator.tr("Saved {}/{} files.").format(success, total))
            logger.info(f"Batch save completed successfully: {success}/{total} files")
            
        self.table.viewport().update()
        self.failed_files.clear()

    def save_all(self):
        dirty_files = [f for f in self.files if f.is_dirty]
        if not dirty_files:
            QMessageBox.information(self, translator.tr("Info"), translator.tr("No changes to save."))
            return
        if not self.confirm_save(dirty_files):
            return
        self.start_batch_save(dirty_files)

    def save_selected(self):
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.warning(self, translator.tr("Warning"), translator.tr("Please select files to save."))
            return
        selected_files = [self.files[i.row()] for i in indexes]
        dirty_files = [f for f in selected_files if f.is_dirty]
        if not dirty_files:
            QMessageBox.information(self, translator.tr("Info"), translator.tr("No changes to save in selected files."))
            return
        if not self.confirm_save(dirty_files):
            return
        self.start_batch_save(dirty_files)

    def show_column_settings(self):
        from ui.column_settings_dialog import ColumnSettingsDialog
        dialog = ColumnSettingsDialog(
            self.model.AVAILABLE_COLUMNS,
            self.model.visible_columns,
            self
        )
        if dialog.exec() == QDialog.Accepted:
            new_columns = dialog.get_selected_columns()
            self.model.set_visible_columns(new_columns)

    def select_all(self):
        """Select all files in the table."""
        if not self.files:
            return
        self.table.selectAll()

    def deselect_all(self):
        """Deselect all files."""
        self.table.clearSelection()

    def invert_selection(self):
        """Invert current selection."""
        if not self.files:
            return
        selection_model = self.table.selectionModel()
        for row in range(len(self.files)):
            index = self.model.index(row, 0)
            if selection_model.isSelected(index):
                selection_model.select(index, QItemSelectionModel.Deselect | QItemSelectionModel.Rows)
            else:
                selection_model.select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)

    def show_help(self):
        """Show usage guide dialog."""
        msg = translator.tr("USAGE_GUIDE_HTML")
        QMessageBox.information(self, translator.tr("Usage Guide"), msg)

    def show_about(self):
        """Show about dialog."""
        from core._version import __version__
        # Format the translated string with version
        msg_template = translator.tr("ABOUT_HTML")
        msg = msg_template.format(version=__version__)
        QMessageBox.about(self, translator.tr("About ComicMeta Editor"), msg)
    
    def check_for_updates(self):
        """Check for updates from GitHub."""
        from core._version import __version__
        from core.updater import UpdateChecker
        from ui.update_dialog import UpdateDialog
        
        # Show progress message
        progress = QProgressDialog(translator.tr("Checking for updates..."), None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)
        progress.show()
        QApplication.processEvents()
        
        # Create worker thread
        class UpdateWorker(QThread):
            finished = Signal(object)
            
            def __init__(self, current_version):
                super().__init__()
                self.current_version = current_version
                
            def run(self):
                checker = UpdateChecker()
                result = checker.check_for_updates(self.current_version)
                self.finished.emit(result)
        
        def on_check_complete(result):
            progress.close()
            
            if result is None:
                QMessageBox.warning(self, translator.tr("Error"), 
                                  translator.tr("Failed to check for updates."))
                return
            
            if result["has_update"]:
                dialog = UpdateDialog(
                    __version__,
                    result["latest_version"],
                    result["release_notes"],
                    result["download_url"],
                    self
                )
                dialog.exec()
            else:
                QMessageBox.information(self, translator.tr("Info"), 
                                      translator.tr("You are using the latest version."))
        
        worker = UpdateWorker(__version__)
        worker.finished.connect(on_check_complete)
        worker.start()
        
        # Store worker to prevent garbage collection
        self._update_worker = worker
