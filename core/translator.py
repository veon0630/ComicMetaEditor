from PySide6.QtCore import QObject, Signal
from core.translations import TRANSLATIONS
from core.settings_manager import settings_manager

class Translator(QObject):
    languageChanged = Signal()

    def __init__(self):
        super().__init__()
        self._translations = TRANSLATIONS
        self._current_lang = "en_US"
        self.load_language()

    def load_language(self):
        self._current_lang = settings_manager.get("language", "en_US")

    def set_language(self, lang_code):
        if lang_code in self._translations or lang_code == "en_US":
            self._current_lang = lang_code
            settings_manager.set("language", lang_code)
            self.languageChanged.emit()

    def tr(self, text, context=None):
        # Always try to look up in current language dict first
        # This allows using keys like "USAGE_GUIDE_HTML" even for en_US
        lang_dict = self._translations.get(self._current_lang, {})
        if text in lang_dict:
            return lang_dict[text]
            
        # Fallback to text itself if not found (default behavior for en_US if not in dict)
        return text
    
    def get_current_language(self):
        return self._current_lang

    def get_available_languages(self):
        """Return a list of available language codes."""
        return list(self._translations.keys())

    def get_languages_with_names(self):
        """Return a dict of {code: display_name} for available languages."""
        result = {}
        for code, data in self._translations.items():
            result[code] = data.get("_LANG_NAME", code)
        return result

# Global instance
translator = Translator()
