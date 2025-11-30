"""
GitHub Releases-based update checker for ComicMeta Editor.
"""
import requests
import os
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
                "download_url": str,
                "assets": list
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
                    "download_url": "",
                    "assets": []
                }
            
            response.raise_for_status()
            release_data = response.json()
            
            # Extract version from tag (remove 'v' prefix if present)
            tag_name = release_data.get("tag_name", "")
            latest_version = tag_name.lstrip("v")
            
            # Extract release notes
            release_notes = release_data.get("body", "No release notes available.")
            
            # Get download URL (HTML URL to the release page)
            html_url = release_data.get("html_url", "")
            
            # Find the zip asset
            download_url = ""
            assets = release_data.get("assets", [])
            for asset in assets:
                if asset["name"].endswith(".zip") and "ComicMetaEditor" in asset["name"]:
                    download_url = asset["browser_download_url"]
                    break
            
            # Fallback to html_url if no zip found
            if not download_url:
                download_url = html_url
            
            # Compare versions
            has_update = self._compare_versions(current_version, latest_version)
            
            logger.info(f"Current: {current_version}, Latest: {latest_version}, Has update: {has_update}")
            
            return {
                "has_update": has_update,
                "latest_version": latest_version,
                "release_notes": release_notes,
                "download_url": download_url,
                "is_zip": download_url.endswith(".zip")
            }
            
        except requests.RequestException as e:
            logger.error(f"Failed to check for updates: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during update check: {e}")
            return None
    
    def download_update(self, url, progress_callback=None):
        """
        Download the update file.
        
        Args:
            url (str): Download URL
            progress_callback (callable): Function to call with progress (0-100)
            
        Returns:
            str: Path to downloaded file, or None if failed
        """
        temp_file = None
        try:
            import tempfile
            
            logger.info(f"Downloading update from: {url}")
            response = requests.get(url, stream=True, timeout=60)  # Increased timeout
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192
            downloaded_size = 0
            
            # Create temp file
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, "ComicMetaEditor_Update.zip")
            
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=block_size):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if total_size > 0 and progress_callback:
                            percent = int((downloaded_size / total_size) * 100)
                            progress_callback(percent)
                            
            logger.info(f"Update downloaded to: {temp_file}")
            return temp_file
            
        except Exception as e:
            logger.error(f"Failed to download update: {e}")
            # Clean up partial download
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    logger.info(f"Cleaned up partial download: {temp_file}")
                except:
                    pass
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
            logger.warning(f"Version comparison failed: {e}, trying segment comparison")
            # Fallback: segment-based comparison
            try:
                def parse_version_tuple(v):
                    """Parse version string to comparable tuple."""
                    # Remove 'v' prefix and any suffix like '-beta'
                    clean_v = v.lstrip('v').split('-')[0]
                    parts = clean_v.split('.')
                    return tuple(int(p) for p in parts if p.isdigit())
                
                current_tuple = parse_version_tuple(current)
                latest_tuple = parse_version_tuple(latest)
                return latest_tuple > current_tuple
            except Exception as e2:
                logger.warning(f"Segment comparison failed: {e2}, falling back to string comparison")
                # Last resort: string comparison
                return latest > current

