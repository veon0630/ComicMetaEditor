# ComicMeta Editor Configuration
"""
Centralized configuration for the ComicMeta Editor application.
All constants and configuration values should be defined here.
"""

class Config:
    """Application-wide configuration constants"""
    
    # ==================== Application Info ====================
    APP_NAME = "ComicMeta Editor"
    
    # ==================== Cache Settings ====================
    COVER_CACHE_SIZE = 50  # Number of covers to cache in memory
    COVER_CACHE_MAX_MB = 100  # Approximate max memory for cover cache
    
    # ==================== Network Settings ====================
    REQUEST_CONNECT_TIMEOUT = 10  # seconds
    REQUEST_READ_TIMEOUT = 30  # seconds
    REQUEST_RETRIES = 3
    RATE_LIMIT_MAX_REQUESTS = 90  # Max requests per window
    RATE_LIMIT_WINDOW_SECONDS = 60  # Time window for rate limiting
    
    # ==================== UI Settings ====================
    PROGRESS_UPDATE_THROTTLE = 0.05  # seconds (50ms)
    TABLE_PAGE_SIZE = 100
    DEFAULT_WINDOW_WIDTH = 1400
    DEFAULT_WINDOW_HEIGHT = 800
    
    # ==================== File Settings ====================
    SUPPORTED_EXTENSIONS = ('.cbz', '.zip')
    TEMP_FILE_PREFIX = '.tmp'
    
    # ==================== Image Settings ====================
    THUMBNAIL_MAX_WIDTH = 300
    THUMBNAIL_MAX_HEIGHT = 450
    THUMBNAIL_QUALITY = 85  # JPEG quality (1-100)
    
    # ==================== Logging Settings ====================
    LOG_DIR = "logs"
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
    LOG_BACKUP_COUNT = 5
    LOG_LEVEL = "INFO"
    
    # ==================== Threading Settings ====================
    MAX_CONCURRENT_SAVES = 4  # Max parallel save operations
    FILE_LOCK_TIMEOUT = 30  # seconds
    
    # ==================== Search/Scraper Settings ====================
    SCRAPER_FUZZY_THRESHOLD = 60  # Minimum fuzzy match score
    SCRAPER_MAX_RESULTS = 15
    
    # ==================== Update Settings ====================
    GITHUB_REPO_OWNER = "veon0630"
    GITHUB_REPO_NAME = "ComicMetaEditor"
    
    @classmethod
    def get_thumbnail_size(cls):
        """Get thumbnail size as tuple"""
        return (cls.THUMBNAIL_MAX_WIDTH, cls.THUMBNAIL_MAX_HEIGHT)
    
    @classmethod
    def get_request_timeout(cls):
        """Get request timeout as tuple (connect, read)"""
        return (cls.REQUEST_CONNECT_TIMEOUT, cls.REQUEST_READ_TIMEOUT)
