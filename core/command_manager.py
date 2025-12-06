from utils.text_utils import get_number
from utils.logger import logger
from core.comic_file import ComicFile
from core.metadata import MetadataMapper
from core.scraper import BangumiScraper

class CommandManager:
    """
    Centralized manager for business logic commands.
    Decouples logic from UI.
    """

    @staticmethod
    def auto_number(files: list[ComicFile], indexes: list) -> list[ComicFile]:
        """
        Apply auto-numbering to selected files based on their filenames.
        Returns list of modified files.
        """
        modified_files = []
        for idx in indexes:
            if idx.row() < len(files):
                file_obj = files[idx.row()]
                
                # Extract number from filename
                num, _ = get_number(file_obj.file_path.stem)
                
                if num is not None:
                    # Format: remove .0 if integer
                    num_str = str(int(num)) if num.is_integer() else str(num)
                    
                    file_obj.set_metadata("Number", num_str)
                    
                    # Optional: Update title if series name exists
                    series = file_obj.metadata.get("Series")
                    if series:
                        file_obj.set_metadata("Title", f"{series} Vol. {num_str}")
                    
                    modified_files.append(file_obj)
        
        return modified_files

    @staticmethod
    def convert_format(files: list[ComicFile], indexes: list, target_ext: str) -> tuple[int, list]:
        """
        Convert selected files to target extension (.zip or .cbz).
        Returns (success_count, failed_list).
        failed_list contains tuples of (filename, error_message).
        """
        success_count = 0
        failed_list = []
        
        for idx in indexes:
            if idx.row() < len(files):
                file_obj = files[idx.row()]
                
                if file_obj.file_path.suffix.lower() == target_ext:
                    continue
                
                try:
                    if file_obj.convert_format(target_ext):
                        success_count += 1
                    else:
                        # Should normally raise exception if fails, but if returns False
                        failed_list.append((file_obj.file_path.name, "Unknown error"))
                except Exception as e:
                    logger.error(f"Failed to convert {file_obj.file_path.name}: {e}")
                    failed_list.append((file_obj.file_path.name, str(e)))
        
        return success_count, failed_list

    @staticmethod
    def apply_scraped_data(files: list[ComicFile], indexes: list, bangumi_data: dict, 
                          mode: str, options: dict, scraper: BangumiScraper, 
                          progress_callback=None) -> tuple[int, list[tuple[str, str]]]:
        """
        Apply scraped metadata to files.
        Handles Series and Volume modes, fetching extra data as needed.
        
        Returns:
            tuple: (success_count, failed_list)
                - success_count: number of files successfully scraped
                - failed_list: list of (filename, error_reason) tuples for failures
        """
        selected_fields = options.get("fields", [])
        
        # Field Mapping
        field_map = {
            "Title": ["Title"],
            "Series": ["Series"],
            "Number": ["Number", "Volume", "Count"],
            "Summary": ["Summary"],
            "Writer": ["Writer"],
            "Publisher": ["Publisher", "Imprint"],
            "Date": ["Year", "Month", "Day"],
            "Genre": ["Genre"],
            "Tags": ["Tags"],
            "CommunityRating": ["CommunityRating"],
            "AgeRating": ["AgeRating"],
            "Status": ["Status"],
            "ISBN": ["ISBN"],
            "Format": ["Format"],
            "Web": ["Web"],
        }
        
        allowed_keys = set()
        for field_key, comic_keys in field_map.items():
            if field_key in selected_fields:
                allowed_keys.update(comic_keys)

        should_apply_cover = "Cover" in selected_fields
        success_count = 0
        failed_list = []

        if mode == 'series':
            # 1. Fetch Series Info
            series_info = MetadataMapper.bangumi_to_comicinfo(bangumi_data)
            series_tags = series_info.get("Tags", "")
            
            # 2. Fetch Volume Map
            volume_map = {}
            try:
                volumes = scraper.get_series_volumes(bangumi_data['id'])
                for v in volumes:
                    volume_map[v['number']] = v
            except Exception as e:
                logger.warning(f"Failed to fetch volumes: {e}")
            
            total_count = len(volume_map) if volume_map else 0
            
            # 3. Apply to files
            for i, idx in enumerate(indexes):
                if progress_callback and progress_callback(i): # Check cancellation
                    break
                
                if idx.row() >= len(files): continue
                file_obj = files[idx.row()]
                filename = file_obj.file_path.name
                
                try:
                    # Determine number
                    num_str = file_obj.get_metadata("Number")
                    if not num_str:
                        num_val, _ = get_number(file_obj.file_path.stem)
                    else:
                        num_val, _ = get_number(num_str)
                    
                    # Base info
                    final_info = series_info.copy()
                    final_info["Genre"] = series_tags
                    final_info["Tags"] = ""
                    
                    volume_fetched = False
                    # Match volume
                    if num_val is not None and num_val in volume_map:
                        vol_data = volume_map[num_val]
                        try:
                            full_vol = scraper.get_subject_metadata(vol_data['id'])
                            if full_vol:
                                vol_info = MetadataMapper.bangumi_to_comicinfo(full_vol)
                                final_info.update(vol_info)
                                final_info["Series"] = series_info["Series"]
                                final_info["Number"] = MetadataMapper._format_number(num_val)
                                final_info["Volume"] = MetadataMapper._format_number(num_val)
                                if total_count > 0:
                                    final_info["Count"] = total_count
                                
                                final_info["Genre"] = series_tags
                                final_info["Tags"] = vol_info.get("Tags", "")
                                volume_fetched = True
                                
                                if should_apply_cover:
                                    cover_data = scraper.get_subject_cover(vol_data['id'])
                                    if cover_data:
                                        file_obj.set_custom_cover(cover_data)
                            else:
                                # API returned None (rate limit or error)
                                failed_list.append((filename, "Rate limit or API error"))
                                logger.warning(f"Failed to fetch metadata for {filename}: API returned None")
                                continue
                        except Exception as e:
                            failed_list.append((filename, f"Volume fetch error: {str(e)}"))
                            logger.warning(f"Failed to fetch volume details for {filename}: {e}")
                            continue
                    
                    # Apply metadata
                    for key, val in final_info.items():
                        if key in allowed_keys and val:
                            file_obj.set_metadata(key, val)
                    
                    success_count += 1
                except Exception as e:
                    failed_list.append((filename, f"Unexpected error: {str(e)}"))
                    logger.error(f"Unexpected error processing {filename}: {e}")

        elif mode == 'volume':
            # 1. Fetch Full Volume Info
            full_vol = scraper.get_subject_metadata(bangumi_data['id'])
            if not full_vol:
                raise Exception("Failed to fetch volume metadata")
                
            vol_info = MetadataMapper.bangumi_to_comicinfo(full_vol)
            volume_tags = vol_info.get("Tags", "")
            volume_title = vol_info.get("Title", "")
            
            # Try to get series info
            series_name = ""
            series_tags = ""
            try:
                related = scraper.get_related_subjects(bangumi_data['id'])
                series_rel = next((r for r in related if r.get("relation") == "系列"), None)
                if series_rel:
                    series_meta = scraper.get_subject_metadata(series_rel['id'])
                    if series_meta:
                        series_mapped = MetadataMapper.bangumi_to_comicinfo(series_meta)
                        series_name = series_mapped.get("Series", "")
                        series_tags = series_mapped.get("Tags", "")
            except Exception as e:
                logger.warning(f"Failed to fetch series info: {e}")

            vol_info["Title"] = volume_title
            if series_name:
                vol_info["Series"] = series_name
            vol_info["Genre"] = series_tags
            vol_info["Tags"] = volume_tags

            # 2. Scrape cover
            cover_data = None
            if should_apply_cover:
                cover_data = scraper.get_subject_cover(bangumi_data['id'])
            
            # 3. Apply to ALL selected files
            for i, idx in enumerate(indexes):
                if progress_callback and progress_callback(i): break
                
                if idx.row() >= len(files): continue
                file_obj = files[idx.row()]
                filename = file_obj.file_path.name
                
                try:
                    existing_series = file_obj.get_metadata("Series")
                    
                    for key, val in vol_info.items():
                        if key in allowed_keys and val:
                            if key == "Series" and not series_name and existing_series:
                                continue
                            file_obj.set_metadata(key, val)
                    
                    if cover_data:
                        file_obj.set_custom_cover(cover_data)
                        
                    success_count += 1
                except Exception as e:
                    failed_list.append((filename, f"Apply error: {str(e)}"))
                    logger.error(f"Failed to apply metadata to {filename}: {e}")

        return success_count, failed_list
