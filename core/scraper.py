import requests
import time
import logging
from enum import Enum
from collections import deque
from functools import wraps
from urllib.parse import quote_plus
from zhconv import convert
from utils.text_utils import get_number

from utils.text_utils import get_number
from utils.text_utils import get_number
from utils.logger import logger

# Module-level cache to persist across Scraper instances
# Key: subject_id, Value: dict (metadata)
_METADATA_CACHE = {}
# Key: subject_id, Value: list (related subjects)
_RELATED_CACHE = {}

try:
    from thefuzz import fuzz
except ImportError:
    fuzz = None
    logger.warning("thefuzz module not found. Fuzzy matching will be disabled.")

# ==================== Enums ====================

class SubjectPlatform(Enum):
    Tv = (1, "TV")
    OVA = (2, "OVA")
    Movie = (3, "剧场版")
    Web = (5, "Web")
    Comic = (1001, "漫画")
    Novel = (1002, "小说")
    Illustration = (1003, "画集")
    Game = (4001, "游戏")

    def __new__(cls, value, cn):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.cn = cn
        return obj

    @classmethod
    def parse(cls, value):
        for member in cls:
            if value == member.value or value == member.cn:
                return member
        return None

class SubjectRelation(Enum):
    SERIES = (1002, "系列")
    OFFPRINT = (1003, "单行本")
    ALBUM = (1004, "画集")

    def __new__(cls, value, cn):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.cn = cn
        return obj

    @classmethod
    def parse(cls, value):
        for member in cls:
            if value == member.value or value == member.cn:
                return member
        return None

# ==================== Rate Limiter ====================

class SlideWindowCounter:
    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()

    def is_allowed(self) -> bool:
        current_time = time.time()
        while self.requests and current_time - self.requests[0] > self.window_seconds:
            self.requests.popleft()
        
        if len(self.requests) < self.max_requests:
            self.requests.append(current_time)
            return True
        return False

def slide_window_rate_limiter(max_requests: int = 90, window_seconds: float = 60, max_retries: int = 3, delay: float = 1):
    def decorator(func):
        limiter = SlideWindowCounter(max_requests, window_seconds)
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries <= max_retries:
                if limiter.is_allowed():
                    return func(*args, **kwargs)
                if retries >= max_retries:
                    logger.warning(f"Rate limit exceeded after {max_retries} retries.")
                    return None
                time.sleep(delay)
                retries += 1
        return wrapper
    return decorator

# ==================== Helper Functions ====================

def compute_name_score_by_fuzzy(name: str, name_cn: str, infobox, target: str) -> int:
    if not fuzz:
        # Fallback to simple containment check
        target = target.lower()
        if target in name.lower() or (name_cn and target in name_cn.lower()):
            return 100
        return 0

    target = target.lower()
    score = fuzz.ratio(name.lower(), target)
    if name_cn:
        score = max(score, fuzz.ratio(name_cn.lower(), target))
    
    if infobox:
        for item in infobox:
            if item["key"] == "别名":
                val = item["value"]
                if isinstance(val, list):
                    for alias in val:
                        v = alias.get("v", "") if isinstance(alias, dict) else str(alias)
                        score = max(score, fuzz.ratio(v.lower(), target))
                else:
                    score = max(score, fuzz.ratio(str(val).lower(), target))
    return score

def resort_search_list(query, results, threshold, data_source):
    if not results:
        return []
    
    # Phase 1: Preliminary scoring based on basic info (No extra API calls)
    pre_sorted = []
    for result in results:
        # Basic score using name and name_cn
        score = compute_name_score_by_fuzzy(
            result.get("name", ""),
            result.get("name_cn", ""),
            None, # No infobox yet
            query,
        )
        result["temp_score"] = score
        pre_sorted.append(result)
    
    # Sort by preliminary score
    pre_sorted.sort(key=lambda x: x["temp_score"], reverse=True)
    
    # Phase 2: Fetch full metadata only for top candidates to save API calls
    # Fetch details for top 8 results (or all if fewer)
    # This reduces API calls from N+1 to min(N, 8)+1
    TOP_N = 8
    final_results = []
    
    for i, result in enumerate(pre_sorted):
        # For top items, fetch full metadata
        if i < TOP_N:
            manga_id = result["id"]
            # This will use cache if available
            manga_metadata = data_source.get_subject_metadata(manga_id)
            
            if not manga_metadata:
                continue
                
            # Determine type label
            if manga_metadata.get("series"):
                manga_metadata["type_label"] = "Series"
            else:
                manga_metadata["type_label"] = "Volume"

            # Re-compute score with full metadata (including infobox/aliases)
            score = compute_name_score_by_fuzzy(
                manga_metadata.get("name", ""),
                manga_metadata.get("name_cn", ""),
                manga_metadata.get("infobox", []),
                query,
            )
            manga_metadata["fuzzScore"] = score
            
            if score >= threshold:
                final_results.append(manga_metadata)
        
        else:
            # For lower ranked items, use basic info if it meets threshold
            # But we mark them as "Unknown" type or assume based on context
            if result["temp_score"] >= threshold:
                # Use the basic result but add necessary fields
                result["fuzzScore"] = result["temp_score"]
                result["type_label"] = "Unknown" # We didn't fetch details
                final_results.append(result)

    final_results.sort(key=lambda x: x["fuzzScore"], reverse=True)
    return final_results

# ==================== Scraper Class ====================

class BangumiScraper:
    BASE_URL = "https://api.bgm.tv"

    def __init__(self, access_token=None, connect_timeout=10, read_timeout=30):
        """
        Initialize Bangumi scraper with timeout configuration.
        
        Args:
            access_token: Optional access token for authenticated requests
            connect_timeout: Connection timeout in seconds (default: 10)
            read_timeout: Read timeout in seconds (default: 30)
        """
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.timeout = (connect_timeout, read_timeout)
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "DAZAO/ComicMetaEditor"
        })
        if access_token:
            self.session.headers["Authorization"] = f"Bearer {access_token}"

    @slide_window_rate_limiter()
    def search_subjects(self, query, threshold=60): # Lowered threshold slightly
        logger.info(f"Scraper searching for: {query}")
        query_cn = convert(query, "zh-cn")
        url = f"{self.BASE_URL}/search/subject/{quote_plus(query_cn)}?responseGroup=small&type=1&max_results=15"
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            if "list" in data and data["list"]:
                results = data["list"]
                logger.info(f"Search returned {len(results)} raw results for: {query}")
                # Resort and filter
                return resort_search_list(query_cn, results, threshold, self)
            
            logger.info(f"No results found for: {query}")
            return []
            
        except requests.exceptions.Timeout:
            logger.error(f"Search timed out after {self.connect_timeout + self.read_timeout}s for query: {query}")
            raise Exception(f"Search request timed out. Please check your network connection and try again.")
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection failed for search query: {query}")
            raise Exception("Unable to connect to Bangumi API. Please check your network connection.")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.warning(f"Rate limit exceeded (429) during search. Waiting...")
                time.sleep(2) # Simple backoff
            logger.error(f"HTTP error during search: {e}")
            raise Exception(f"Bangumi API returned an error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise Exception(f"Search failed: {str(e)}")

    @slide_window_rate_limiter()
    def get_subject_metadata(self, subject_id):
        # Check cache first
        if subject_id in _METADATA_CACHE:
            return _METADATA_CACHE[subject_id]
            
        logger.info(f"Fetching metadata for subject ID: {subject_id}")
        url = f"{self.BASE_URL}/v0/subjects/{subject_id}"
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            # Cache the result
            _METADATA_CACHE[subject_id] = data
            return data
        except requests.exceptions.Timeout:
            logger.error(f"Metadata request timed out for subject {subject_id}")
            raise Exception(f"Request timed out while fetching metadata. Please try again.")
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection failed for subject {subject_id}")
            raise Exception("Unable to connect to Bangumi API. Please check your network connection.")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching metadata for {subject_id}: {e}")
            raise Exception(f"Failed to fetch metadata: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Get metadata failed for {subject_id}: {e}")
            raise Exception(f"Failed to get metadata: {str(e)}")



    @slide_window_rate_limiter()
    def get_related_subjects(self, subject_id):
        # Check cache first
        if subject_id in _RELATED_CACHE:
            return _RELATED_CACHE[subject_id]
            
        logger.info(f"Fetching related subjects for ID: {subject_id}")
        url = f"{self.BASE_URL}/v0/subjects/{subject_id}/subjects"
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            # Cache the result
            _RELATED_CACHE[subject_id] = data
            return data
        except requests.exceptions.Timeout:
            logger.error(f"Related subjects request timed out for {subject_id}")
            raise Exception(f"Request timed out while fetching volumes. Please try again.")
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection failed while fetching related subjects for {subject_id}")
            raise Exception("Unable to connect to Bangumi API. Please check your network connection.")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching related subjects for {subject_id}: {e}")
            raise Exception(f"Failed to fetch volumes: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Get related subjects failed for {subject_id}: {e}")
            raise Exception(f"Failed to get volumes: {str(e)}")

    def get_series_volumes(self, subject_id):
        """
        Fetch related 'single volume' subjects and parse their numbers.
        Returns a list of dicts: {'id': int, 'number': float, 'title': str}
        """
        related = self.get_related_subjects(subject_id)
        volumes = []
        
        for rel in related:
            # Check if it is a single volume (Offprint)
            relation_type = SubjectRelation.parse(rel.get("relation"))
            if relation_type == SubjectRelation.OFFPRINT:
                name = rel.get("name_cn") or rel.get("name")
                number, _ = get_number(name)
                
                if number is not None:
                    volumes.append({
                        "id": rel.get("id"),
                        "number": number,
                        "title": name,
                        "relation": rel.get("relation")
                    })
                    
        return volumes

    def get_cover_image(self, url):
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.content
        except requests.exceptions.Timeout:
            logger.error(f"Cover image download timed out: {url}")
            return None
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection failed while downloading cover: {url}")
            return None
        except Exception as e:
            logger.error(f"Failed to download cover: {e}")
            return None

    def get_subject_cover(self, subject_id, size='large'):
        """
        Get cover image for a subject.
        
        Args:
            subject_id: Bangumi subject ID
            size: Image size - 'large', 'common', 'medium', 'small', 'grid'
            
        Returns:
            bytes: Image data, or None if failed
        """
        metadata = self.get_subject_metadata(subject_id)
        if not metadata or 'images' not in metadata:
            return None
            
        try:
            image_url = metadata['images'].get(size)
            if not image_url:
                # Fallback to any available size
                for fallback_size in ['large', 'common', 'medium', 'small']:
                    image_url = metadata['images'].get(fallback_size)
                    if image_url:
                        break
            
            if image_url:
                logger.info(f"Downloading cover image from: {image_url}")
                return self.get_cover_image(image_url)
        except Exception as e:
            logger.error(f"Failed to get cover for subject {subject_id}: {e}")
        
        return None
