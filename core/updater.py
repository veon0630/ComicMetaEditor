"""
GitHub Releases-based update checker for ComicMeta Editor.
"""
import requests
from packaging import version
from config import Config
from utils.logger import logger


class UpdateChecker:
    """Check for updates using GitHub Releases API."""
    
    def __init__(self):
        self.api_url = f"https://api.github.com/repos/{Config.GITHUB_REPO_OWNER}/{Config.GITHUB_REPO_NAME}/releases/latest"
    
    def check_for_updates(self, current_version):
        """
        Check if a new version is available on GitHub.
        
        Args:
            current_version (str): Current version string (e.g., "1.7.3")
            
        Returns:
            dict or None: {
                "has_update": bool,
                "latest_version": str,
                "release_notes": str,
                "download_url": str
            } if successful, None if error
        """
        try:
            logger.info(f"Checking for updates from: {self.api_url}")
            response = requests.get(self.api_url, timeout=10)
            
            # If no releases found
            if response.status_code == 404:
                logger.info("No releases found on GitHub")
                return {
                    "has_update": False,
                    "latest_version": current_version,
                    "release_notes": "",
                    "download_url": ""
                }
            
            response.raise_for_status()
            release_data = response.json()
            
            # Extract version from tag (remove 'v' prefix if present)
            tag_name = release_data.get("tag_name", "")
            latest_version = tag_name.lstrip("v")
            
            # Extract release notes
            release_notes = release_data.get("body", "No release notes available.")
            
            # Get download URL (HTML URL to the release page)
            download_url = release_data.get("html_url", "")
            
            # Compare versions
            has_update = self._compare_versions(current_version, latest_version)
            
            logger.info(f"Current: {current_version}, Latest: {latest_version}, Has update: {has_update}")
            
            return {
                "has_update": has_update,
                "latest_version": latest_version,
                "release_notes": release_notes,
                "download_url": download_url
            }
            
        except requests.RequestException as e:
            logger.error(f"Failed to check for updates: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during update check: {e}")
            return None
    
    def _compare_versions(self, current, latest):
        """
        Compare two version strings using semantic versioning.
        
        Args:
            current (str): Current version
            latest (str): Latest version
            
        Returns:
            bool: True if latest > current
        """
        try:
            return version.parse(latest) > version.parse(current)
        except Exception as e:
            logger.warning(f"Version comparison failed: {e}, doing string comparison")
            # Fallback to string comparison
            return latest > current
