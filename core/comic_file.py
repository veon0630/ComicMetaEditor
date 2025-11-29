import os
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from PIL import Image
import io
import threading
import uuid
from functools import lru_cache
from natsort import natsorted
from xml.dom import minidom
from typing import Optional, Tuple, Dict, Any

from config import Config
from utils.logger import logger

# Global cache for cover images - Module level to avoid memory leaks
@lru_cache(maxsize=Config.COVER_CACHE_SIZE)
def _read_cover_from_zip_cached(file_path_str: str) -> Optional[bytes]:
    """
    Global cached function to read cover from zip file.
    Use module-level function to avoid lru_cache memory leaks with instance methods.
    
    Args:
        file_path_str: Path to the zip file as string (for hashability)
        
    Returns:
        Cover image data as bytes, or None if not found or error occurred
    """
    try:
        with zipfile.ZipFile(file_path_str, 'r') as zf:
            # Helper to decode filename
            def decode_filename(zinfo):
                if zinfo.flag_bits & 0x800:
                    return zinfo.filename
                try:
                    return zinfo.filename.encode('cp437').decode('gbk')
                except (UnicodeDecodeError, UnicodeEncodeError, AttributeError):
                    return zinfo.filename
            
            # Build decoded name map
            decoded_map = {}
            for info in zf.infolist():
                decoded = decode_filename(info)
                decoded_map[decoded] = info.filename
            
            # Find image files
            image_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp')
            all_images = [name for name in decoded_map.keys() if name.lower().endswith(image_extensions)]
            
            if not all_images:
                return None
            
            # Priority 1: Explicit cover files
            cover_names = ['cover', 'folder', 'default', 'poster']
            for img_name in all_images:
                basename = Path(img_name).stem.lower()
                if basename in cover_names:
                    with zf.open(decoded_map[img_name]) as f:
                        return f.read()
            
            # Priority 2: First page (naturally sorted)
            sorted_images = natsorted(all_images)
            first_img = sorted_images[0]
            with zf.open(decoded_map[first_img]) as f:
                return f.read()
                
    except Exception as e:
        logger.error(f"Error reading cover from {file_path_str}: {e}")
        return None

class ComicFile:
    """
    Represents a comic book archive file (.cbz or .zip).
    
    Handles reading and writing metadata (ComicInfo.xml),
    cover images, and file format conversion.
    
    Attributes:
        file_path (Path): Path to the comic file
        metadata (Dict[str, Any]): Comic metadata fields
        is_dirty (bool): Whether metadata has been modified
        custom_cover_data (Optional[bytes]): Custom cover image data
    """
    
    # Class-level file locks to prevent concurrent saves to the same file
    _file_locks: Dict[str, threading.Lock] = {}
    _locks_lock = threading.Lock()
    
    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.metadata = {}
        # self.cover_image_data = None  # Removed to save memory, use get_cover()
        self.cover_filename = None  # Track the original cover filename
        self.custom_cover_data = None  # Store custom/scraped cover
        self.is_dirty = False
        self.original_metadata = {}
        self.zip_name_map = {} # Map correct_filename -> internal_filename
        
        # Default metadata structure
        self.default_metadata = {
            "Series": "",
            "Title": "",
            "Number": "",
            "Count": "",
            "Volume": "",
            "Summary": "",
            "Notes": "",
            "Year": "",
            "Month": "",
            "Day": "",
            "Writer": "",
            "Penciller": "",
            "Inker": "",
            "Colorist": "",
            "Letterer": "",
            "CoverArtist": "",
            "Editor": "",
            "Publisher": "",
            "Imprint": "",
            "Genre": "",
            "Web": "",
            "LanguageISO": "",
            "Format": "",
            "ISBN": "",
            "BlackAndWhite": "Unknown",
            "Manga": "YesAndRightToLeft",
            "Characters": "",
            "Teams": "",
            "Locations": "",
            "ScanInformation": "",
            "StoryArc": "",
            "SeriesGroup": "",
            "CommunityRating": "",
            "Status": "",
            "Tags": "",
            "Pages": {} # For storing page info if needed
        }
        
        self.load()

    def _decode_filename(self, zinfo):
        """Helper to decode filename from ZipInfo, handling GBK/CP437 issues."""
        if zinfo.flag_bits & 0x800:
            return zinfo.filename
        
        # Try to decode as GBK if it was interpreted as CP437
        try:
            raw_bytes = zinfo.filename.encode('cp437')
            return raw_bytes.decode('gbk')
        except:
            return zinfo.filename

    def load(self):
        """Load metadata from the file. Cover is lazy loaded."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")

        try:
            with zipfile.ZipFile(self.file_path, 'r') as zf:
                # Build name map
                self.zip_name_map = {}
                for zinfo in zf.infolist():
                    decoded_name = self._decode_filename(zinfo)
                    self.zip_name_map[decoded_name] = zinfo.filename

                # 1. Load ComicInfo.xml
                xml_internal_name = None
                for name, internal in self.zip_name_map.items():
                    if name == 'ComicInfo.xml':
                        xml_internal_name = internal
                        break
                
                if xml_internal_name:
                    with zf.open(xml_internal_name) as xml_file:
                        self.metadata = self._parse_xml(xml_file)
                else:
                    self.metadata = self.default_metadata.copy()
                    # Auto-inference logic
                    self.metadata["Series"] = self.file_path.parent.name
                    self.metadata["Title"] = self.file_path.stem
                    
                    from utils.text_utils import get_number
                    num_val, _ = get_number(self.file_path.stem)
                    if num_val is not None:
                        if num_val.is_integer():
                            self.metadata["Number"] = str(int(num_val))
                        else:
                            self.metadata["Number"] = str(num_val)

                self.original_metadata = self.metadata.copy()

                # 2. Cover is NOT loaded here anymore to save memory/time

        except zipfile.BadZipFile:
            logger.error(f"Bad Zip File: {self.file_path}")
            self.metadata = self.default_metadata.copy()

    def _parse_xml(self, xml_file):
        """Parse ComicInfo.xml into a dictionary."""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            data = self.default_metadata.copy()
            
            for child in root:
                if child.tag in data:
                    data[child.tag] = child.text if child.text else ""
            
            return data
        except ET.ParseError as e:
            logger.warning(f"Error parsing XML for {self.file_path}: {e}")
            return self.default_metadata.copy()

    # Removed instance method, now using module-level cached function

    def get_cover(self) -> Optional[bytes]:
        """Get cover image data (bytes). Uses module-level cache."""
        if self.custom_cover_data:
            return self.custom_cover_data
            
        # Use module-level cached function (avoids lru_cache memory leak)
        return _read_cover_from_zip_cached(str(self.file_path))
    
    def get_cover_thumbnail(self, max_size: Tuple[int, int] = (300, 450), quality: int = 85) -> Optional[bytes]:
        """
        Get cover image as thumbnail to save memory.
        
        Args:
            max_size: Tuple (width, height) for max dimensions
            quality: JPEG quality 1-100 (lower = smaller file)
            
        Returns:
            bytes: Thumbnail image data, or None if failed
        """
        cover_data = self.get_cover()
        if not cover_data:
            return None
        
        try:
            from io import BytesIO
            img = Image.open(BytesIO(cover_data))
            
            # Only resize if image is larger than max_size
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Convert to bytes
            output = BytesIO()
            img_format = img.format or 'JPEG'
            if img_format == 'JPEG':
                img.save(output, format=img_format, quality=quality, optimize=True)
            else:
                img.save(output, format=img_format, optimize=True)
            
            return output.getvalue()
        except Exception as e:
            logger.error(f"Error creating thumbnail: {e}")
            return cover_data  # Return original if thumbnail fails

    def _extract_cover(self, zf):
        """Deprecated: Logic moved to _read_cover_from_zip_cached for lazy loading."""
        pass

    def _needs_repack(self):
        """
        Check if we need to repack the entire zip or can use append mode.
        
        Returns:
            bool: True if repack is needed, False if append mode can be used
        """
        # Check if zip contains non-ASCII filenames
        # Append mode can corrupt encoding for non-ASCII filenames
        for name in self.zip_name_map.keys():
            try:
                name.encode('ascii')
            except UnicodeEncodeError:
                # Contains non-ASCII characters (e.g., Chinese, Japanese)
                # Must use repack mode to preserve encoding
                return True
        
        # If we have a custom cover, check if we need to delete old covers
        if self.custom_cover_data:
            cover_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp')
            cover_names = ['cover', 'folder', 'default', 'poster']
            
            # Check if any existing cover files need to be removed
            for name in self.zip_name_map.keys():
                basename = Path(name).stem.lower()
                ext = Path(name).suffix.lower()
                if basename in cover_names and ext in cover_extensions:
                    return True  # Need to delete old cover, must repack
        
        # Check if ComicInfo.xml already exists
        for name in self.zip_name_map.keys():
            if name == 'ComicInfo.xml':
                return True  # Need to update existing ComicInfo.xml, must repack
        
        # Can use append mode (only for pure ASCII filenames)
        return False
    
    def _detect_cover_filename(self):
        """Detect the filename for custom cover based on image format."""
        try:
            from io import BytesIO
            img = Image.open(BytesIO(self.custom_cover_data))
            img_format = img.format.lower()
            
            # Map PIL format names to extensions
            if img_format == 'jpeg':
                return 'cover.jpg'
            else:
                return f'cover.{img_format}'
        except Exception:
            # Fallback to jpg if detection fails
            return 'cover.jpg'
    
    def _save_with_append(self):
        """
        Fast path: append ComicInfo.xml and/or cover to existing zip.
        Only used when no existing ComicInfo.xml and no cover files to replace.
        
        Note: We don't set UTF-8 flag here to avoid mixed encoding issues.
        ComicInfo.xml and cover.* are ASCII filenames so they don't need UTF-8.
        """
        try:
            with zipfile.ZipFile(self.file_path, 'a', zipfile.ZIP_DEFLATED) as zf:
                # Write ComicInfo.xml (ASCII filename, no UTF-8 flag needed)
                xml_str = self._generate_xml()
                zinfo = zipfile.ZipInfo(
                    filename='ComicInfo.xml',
                    date_time=datetime.now().timetuple()[:6]
                )
                # Don't set UTF-8 flag to avoid mixed encoding with existing files
                zf.writestr(zinfo, xml_str.encode('utf-8'))
                
                # Write custom cover if provided
                if self.custom_cover_data:
                    cover_filename = self._detect_cover_filename()
                    zinfo_cover = zipfile.ZipInfo(
                        filename=cover_filename,
                        date_time=datetime.now().timetuple()[:6]
                    )
                    # Don't set UTF-8 flag (cover.* is ASCII)
                    zf.writestr(zinfo_cover, self.custom_cover_data)
                    
                    # Update tracking
                    self.cover_filename = cover_filename
                    # self.cover_image_data = self.custom_cover_data # Removed
            
            self.is_dirty = False
            self.original_metadata = self.metadata.copy()
            
            # Invalidate cache (clears all cached covers, acceptable for correctness)
            _read_cover_from_zip_cached.cache_clear()
            
        except Exception as e:
            logger.error(f"Error appending to file {self.file_path}: {e}")
            raise e
    
    def _save_with_repack(self, progress_callback=None):
        """
        Slow path: repack the entire zip with updated ComicInfo.xml and cover.
        Required when updating existing ComicInfo.xml or replacing cover files.
        """
        # Use unique temp file name to avoid concurrent write conflicts
        temp_path = self.file_path.with_suffix(f'.tmp.{uuid.uuid4().hex[:8]}')
        
        try:
            # Copy all files from original zip to new zip
            with zipfile.ZipFile(self.file_path, 'r') as zin:
                with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zout:
                    # Step 1: Copy all files except ComicInfo.xml and cover.* files
                    cover_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp')
                    cover_names = ['cover', 'folder', 'default', 'poster']
                    
                    # Calculate total size for progress
                    total_size = sum(item.file_size for item in zin.infolist())
                    current_size = 0
                    
                    for i, item in enumerate(zin.infolist()):
                        # Decode the name to check what it is
                        decoded_name = self._decode_filename(item)
                        
                        # Skip ComicInfo.xml (we'll write a new one)
                        if decoded_name == 'ComicInfo.xml':
                            current_size += item.file_size
                            continue
                        
                        # Skip existing cover.* files if we have a custom cover
                        if self.custom_cover_data:
                            basename = Path(decoded_name).stem.lower()
                            ext = Path(decoded_name).suffix.lower()
                            if basename in cover_names and ext in cover_extensions:
                                current_size += item.file_size
                                continue
                        
                        # Copy all other files with UTF-8 encoding
                        zinfo_new = zipfile.ZipInfo(
                            filename=decoded_name,
                            date_time=item.date_time
                        )
                        zinfo_new.compress_type = item.compress_type
                        zinfo_new.flag_bits |= 0x800  # Set UTF-8 flag
                        zout.writestr(zinfo_new, zin.read(item.filename))
                        
                        current_size += item.file_size
                        if progress_callback and total_size > 0:
                            # Report progress (0-100)
                            progress_callback(int(current_size / total_size * 100))
                    
                    # Step 2: Write custom cover if provided
                    if self.custom_cover_data:
                        cover_filename = self._detect_cover_filename()
                        zinfo_cover = zipfile.ZipInfo(
                            filename=cover_filename,
                            date_time=datetime.now().timetuple()[:6]
                        )
                        zinfo_cover.flag_bits |= 0x800  # Set UTF-8 flag
                        zout.writestr(zinfo_cover, self.custom_cover_data)
                        
                        # Update tracking
                        self.cover_filename = cover_filename
                        # self.cover_image_data = self.custom_cover_data # Removed
                    
                    # Step 3: Write new ComicInfo.xml
                    xml_str = self._generate_xml()
                    zinfo_xml = zipfile.ZipInfo(
                        filename='ComicInfo.xml',
                        date_time=datetime.now().timetuple()[:6]
                    )
                    zinfo_xml.flag_bits |= 0x800  # Set UTF-8 flag
                    zout.writestr(zinfo_xml, xml_str.encode('utf-8'))
            
            # Replace original file
            if self.file_path.exists():
                self.file_path.unlink()
            temp_path.rename(self.file_path)
            
            self.is_dirty = False
            self.original_metadata = self.metadata.copy()
            
            # Invalidate cache for this specific file
            # Note: lru_cache.cache_clear() clears ALL cache, but acceptable for correctness
            _read_cover_from_zip_cached.cache_clear()
            
        except Exception as e:
            logger.error(f"Error repacking file {self.file_path}: {e}")
            if temp_path.exists():
                temp_path.unlink()
            raise e
    
    def save(self, progress_callback=None):
        """Save metadata and custom cover back to the file. Thread-safe."""
        if not self.is_dirty and not self.custom_cover_data:
            return
        
        logger.info(f"Saving comic file: {self.file_path.name}")
        
        # Acquire file lock to prevent concurrent saves to the same file
        file_path_str = str(self.file_path)
        with self._locks_lock:
            if file_path_str not in self._file_locks:
                self._file_locks[file_path_str] = threading.Lock()
            file_lock = self._file_locks[file_path_str]
        
        # Perform save with lock
        with file_lock:
            # Decide which save method to use
            if self._needs_repack():
                # Slow path: must repack entire zip
                self._save_with_repack(progress_callback)
            else:
                # Fast path: can append to existing zip
                self._save_with_append()

    def _generate_xml(self):
        """Generate ComicInfo.xml string from metadata. Optimized version."""
        root = ET.Element("ComicInfo")
        root.set("xmlns:xsd", "http://www.w3.org/2001/XMLSchema")
        root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")

        # Order matters for some readers, but generally standard fields first is good
        for key, value in self.metadata.items():
            if key == "Pages": continue # Skip internal pages list
            
            if value: # Only write non-empty fields
                sub = ET.SubElement(root, key)
                sub.text = str(value)

        # Pretty print with minidom (imported at module level)
        xml_str = ET.tostring(root, encoding='utf-8', method='xml')
        parsed = minidom.parseString(xml_str)
        pretty_xml = parsed.toprettyxml(indent="  ")
        
        # Remove excessive blank lines
        lines = [line for line in pretty_xml.split('\n') if line.strip()]
        return '\n'.join(lines)

    def set_metadata(self, key, value):
        """Update a metadata field."""
        if key in self.metadata and self.metadata[key] != value:
            self.metadata[key] = value
            self.is_dirty = True

    def get_metadata(self, key):
        return self.metadata.get(key, "")

    def convert_format(self, target_extension):
        """
        Convert file format between .zip and .cbz by renaming.
        
        Args:
            target_extension: '.zip' or '.cbz'
            
        Returns:
            bool: True if conversion successful, False otherwise
        """
        if target_extension not in ['.zip', '.cbz']:
            raise ValueError(f"Invalid extension: {target_extension}")
            
        current_ext = self.file_path.suffix.lower()
        if current_ext == target_extension:
            return False  # Already in target format
            
        # Create new path with target extension
        new_path = self.file_path.with_suffix(target_extension)
        
        try:
            # Rename the file
            logger.info(f"Converting {self.file_path.name} to {target_extension}")
            self.file_path.rename(new_path)
            self.file_path = new_path
            return True
        except Exception as e:
            logger.error(f"Error converting format: {e}")
            return False

    def set_custom_cover(self, cover_data):
        """
        Set a custom cover image (from scraping or manual upload).
        
        Args:
            cover_data: bytes - Image data
        """
        if cover_data:
            self.custom_cover_data = cover_data
            # self.cover_image_data = cover_data  # Removed
            self.is_dirty = True  # Mark for saving
