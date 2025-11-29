# Mapping from Bangumi fields to ComicInfo fields
from typing import Dict, Any, Optional

class MetadataMapper:
    """
    Utility class for converting metadata between different formats.
    
    Currently supports converting Bangumi metadata to ComicInfo.xml format.
    """
    
    @staticmethod
    def _format_number(value: Any) -> str:
        """
        Format a number to remove .0 for integers.
        Args:
            value: int, float, or str
        Returns:
            str: Formatted number string
        """
        if value is None or value == "":
            return ""
        
        try:
            num = float(value)
            # If it's a whole number, return as integer string
            if num.is_integer():
                return str(int(num))
            else:
                return str(num)
        except (ValueError, TypeError):
            return str(value)
    
    @staticmethod
    def bangumi_to_comicinfo(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Bangumi metadata to ComicInfo format with validation.
        
        Args:
            data: Dictionary containing Bangumi subject metadata
                 Expected keys: name_cn, name, summary, date, infobox,
                 rating, tags, platform, etc.
        
        Returns:
            Dictionary with ComicInfo.xml compatible fields:
            - Series, Title, Summary, Writer, Publisher
            - Year, Month, Day, Genre, Tags
            - CommunityRating, Status, Format, etc.
        """
        # Validate input
        if not data or not isinstance(data, dict):
            return {}
        
        info = {}
        
        # Basic Info - with safe access
        info["Series"] = data.get("name_cn") or data.get("name") or ""
        info["Title"] = info["Series"] # Default title to series name
        info["Summary"] = data.get("summary") or ""
        
        subject_id = data.get('id')
        if subject_id:
            info["Web"] = f"https://bgm.tv/subject/{subject_id}"
        else:
            info["Web"] = ""
        
        # Date
        if data.get("date"):
            try:
                parts = data["date"].split("-")
                if len(parts) >= 1: info["Year"] = int(parts[0])
                if len(parts) >= 2: info["Month"] = int(parts[1])
                if len(parts) >= 3: info["Day"] = int(parts[2])
            except (ValueError, IndexError, TypeError) as e:
                # Invalid date format, skip
                pass

        # Infobox parsing
        infobox = data.get("infobox", [])
        publishers = []
        magazines = []
        
        if infobox:
            for item in infobox:
                key = item.get("key")
                val = item.get("value")
                
                # Helper to get string value
                def get_val_str(v: Any) -> str:
                    if isinstance(v, list):
                        # Check if list of dicts or strings
                        if v and isinstance(v[0], dict):
                            return ",".join([x.get("v", "") for x in v])
                        return ",".join([str(x) for x in v])
                    return str(v)

                if key == "作者":
                    info["Writer"] = get_val_str(val)
                elif key == "出版社":
                    # BangumiKomga takes the first publisher
                    if isinstance(val, list) and val:
                        if isinstance(val[0], dict):
                            info["Publisher"] = val[0].get("v") or ""
                        else:
                            info["Publisher"] = str(val[0]) if val[0] else ""
                    elif val:
                        info["Publisher"] = str(val)
                elif "ISBN" in key.upper():
                    info["ISBN"] = get_val_str(val).strip()
                elif key == "连载杂志":
                    if isinstance(val, list):
                        if val and isinstance(val[0], dict):
                             magazines.extend([x.get("v", "") for x in val])
                        else:
                             magazines.extend([str(x) for x in val])
                    else:
                        magazines.append(str(val))
                
                # Status Mapping
                # runningLang = ["放送", "放送（連載）中"]
                # abandonedLang = ["打ち切り"]
                # endedLang = ["完結", "结束", "连载结束"]
                if key in ["放送开始", "连载开始"]:
                     pass # Just date
                
                if key in ["结束", "连载结束", "完结"]:
                     pass

        # Status Logic (Iterate again to find status keys)
        status = "Ongoing" # Default
        running_keys = ["放送", "放送（連載）中", "连载"]
        abandoned_keys = ["打ち切り"]
        ended_keys = ["完結", "结束", "连载结束"]
        
        for item in infobox:
            key = item.get("key")
            if key in running_keys:
                status = "Ongoing"
            elif key in abandoned_keys:
                status = "Abandoned"
                break # Priority
            elif key in ended_keys:
                status = "Ended"
                break
        info["Status"] = status

        # Genre - Only magazines (platform and score removed)
        genres = []
        
        # Add magazines to genre
        genres.extend(magazines)
        
        info["Genre"] = ",".join(genres) if genres else ""
        
        # Format (separate from Genre)
        platform = data.get("platform")
        if platform:
            if platform == "漫画":
                info["Format"] = "Comic"
            elif platform == "小说":
                info["Format"] = "Novel"
            elif platform == "画集":
                info["Format"] = "Artbook"
            else:
                info["Format"] = platform

        # Rating (stored separately, not in Genre)
        rating = data.get("rating")
        if rating and isinstance(rating, dict):
            score = rating.get("score", 0)
            if score and score > 0:
                info["CommunityRating"] = score

        # Tags (Separate from Genre!)
        tags = data.get("tags", [])
        tag_list = []
        
        # BangumiKomga logic: filter tags by count >= 3
        for t in tags:
            name = t.get("name", "")
            count = t.get("count", 0)
            
            # Only add tags with count >= 3
            if count >= 3:
                tag_list.append(name)
                
        info["Tags"] = ",".join(tag_list)

        # Manga specific
        info["Manga"] = "YesAndRightToLeft" 

        return info
