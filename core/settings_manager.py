import json
import os
import sys
from utils.logger import logger

class SettingsManager:
    """
    Manages application settings using a local JSON file.
    This replaces QSettings to make the application portable.
    """
    
    def __init__(self, filename="settings.json"):
        # Determine the base path
        if getattr(sys, 'frozen', False):
            # If running as compiled exe
            base_path = os.path.dirname(sys.executable)
        else:
            # If running as script
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        self.filename = os.path.join(base_path, filename)
        self.settings = {}
        self.load()
        
    def load(self):
        """Load settings from the JSON file."""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
                logger.info(f"Loaded settings from {self.filename}")
                
                # Check and update version
                from core._version import __version__
                if self.settings.get('_version') != __version__:
                    self.settings['_version'] = __version__
                    self.save()
                    
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
                self.settings = {}
        else:
            logger.info("No settings file found, using defaults")
            self.settings = {}
            
    def save(self):
        """Save current settings to the JSON file."""
        try:
            # Ensure version is always saved
            from core._version import __version__
            self.settings['_version'] = __version__
            
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            logger.info(f"Saved settings to {self.filename}")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            
    def get(self, key, default=None):
        """Get a setting value."""
        return self.settings.get(key, default)
        
    def set(self, key, value):
        """Set a setting value and save immediately."""
        self.settings[key] = value
        self.save()

# Global instance
settings_manager = SettingsManager()
