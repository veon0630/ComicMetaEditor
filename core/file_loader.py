import os
from pathlib import Path
from natsort import natsorted
from core.comic_file import ComicFile
from utils.logger import logger

class FileLoader:
    """
    Handles scanning and loading of comic files from the filesystem.
    Pure logic class, no UI dependencies.
    """
    
    @staticmethod
    def scan_directory(folder_path: Path) -> list[Path]:
        """
        Scan a directory for supported comic files (.cbz, .zip).
        Returns a sorted list of file paths.
        """
        paths = []
        try:
            for item in folder_path.iterdir():
                if item.is_file() and item.suffix.lower() in ('.cbz', '.zip'):
                    paths.append(item)
            
            # Sort naturally (Vol 1, Vol 2, ... Vol 10)
            return natsorted(paths, key=lambda p: p.name)
        except Exception as e:
            logger.error(f"Error scanning directory {folder_path}: {e}")
            raise e

    @staticmethod
    def load_file(file_path: Path) -> ComicFile:
        """
        Load a single comic file.
        """
        try:
            return ComicFile(file_path)
        except Exception as e:
            logger.error(f"Error loading file {file_path}: {e}")
            raise e
