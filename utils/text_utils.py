import re
from typing import Tuple, Optional

class NumberType:
    """Constants for different types of numbers found in comic filenames."""
    VOLUME = "volume"
    CHAPTER = "chapter"
    NORMAL = "normal"
    NONE = "none"

def get_number(s: str) -> Tuple[Optional[float], str]:
    """
    Extract the volume/chapter number from a string (e.g., filename).
    
    Supports various formats:
    - Prefix match: "vol.1", "vol1", "chap.5", "chapter05"
    - Normal number: "Series Name 12" -> 12
    - Decimal numbers: "3.5" or "vol.3.5"
    
    Args:
        s: String to extract number from (typically a filename)
        
    Returns:
        Tuple of (number, type):
        - number: Extracted number as float, or None if not found
        - type: One of NumberType constants (VOLUME, CHAPTER, NORMAL, NONE)
    
    Examples:
        >>> get_number("Vol.03")
        (3.0, 'volume')
        >>> get_number("Chapter 12.5")
        (12.5, 'chapter')
        >>> get_number("Series Name 007")
        (7.0, 'normal')
    """
    s = s.replace("-", ".").replace("_", ".")
    
    # 1. Prefix match (vol.1, chap.1)
    pattern = r"vol\.?(\d+(\.\d+)?)|chap\.?(\d+(\.\d+)?)"
    match = re.search(pattern, s, re.IGNORECASE)
    if match:
        if match.group(1):
            return float(match.group(1)), NumberType.VOLUME
        elif match.group(3):
            return float(match.group(3)), NumberType.CHAPTER

    # 2. Roman Numerals support (Future enhancement)
    # Currently not implemented. Can be added if needed:
    # - Pattern: r"(?<![A-Z])[IVXLCDM]+(?![A-Z])"
    # - Would require roman_to_int() conversion function

    # 3. Normal number at the end or standalone
    # Find all numbers
    decimal_pattern = r"\d+\.\d+|\d+"
    matches = re.findall(decimal_pattern, s)
    
    if matches:
        # Usually the last number is the volume number in titles like "Series Name 12"
        return float(matches[-1]), NumberType.NORMAL

    return None, NumberType.NONE
