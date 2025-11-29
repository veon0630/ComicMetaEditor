import sys
import re
from pathlib import Path

def update_version(new_version):
    # Normalize version format
    # Supports: 1.5, 1.5.0, 1.5.0.0
    parts = new_version.strip().split('.')
    if not all(p.isdigit() for p in parts):
        print("Error: Version must contain only numbers and dots (e.g., 1.5, 1.5.0)")
        sys.exit(1)
        
    int_parts = [int(p) for p in parts]
    
    # Generate tuple for Windows resource (always 4 items)
    tuple_parts = int_parts + [0] * (4 - len(int_parts))
    tuple_parts = tuple_parts[:4]
    version_tuple = f"({tuple_parts[0]}, {tuple_parts[1]}, {tuple_parts[2]}, {tuple_parts[3]})"
    
    # Generate string for Python (at least 3 items, preserve more if given)
    string_parts = int_parts + [0] * (3 - len(int_parts))
    # If input had more than 3 parts (e.g. 1.5.0.1), keep them. 
    # If input was 1.5, it becomes 1.5.0.
    if len(int_parts) > 3:
        string_parts = int_parts
    else:
        string_parts = string_parts[:3]
        
    final_version_string = ".".join(map(str, string_parts))
    
    print(f"Version: {final_version_string}")
    print(f"Tuple:   {version_tuple}")

    # Base path relative to this script
    base_path = Path(__file__).parent

    # 1. Update core/_version.py
    version_file = base_path / "core/_version.py"
    if version_file.exists():
        content = version_file.read_text(encoding='utf-8')
        new_content = re.sub(r'__version__ = ".*"', f'__version__ = "{final_version_string}"', content)
        version_file.write_text(new_content, encoding='utf-8')
        print(f"Updated {version_file}")
    else:
        print(f"Warning: {version_file} not found")

    # 2. Update version_info.txt
    info_file = base_path / "version_info.txt"
    if info_file.exists():
        content = info_file.read_text(encoding='utf-8')
        
        # Update filevers and prodvers
        content = re.sub(r'filevers=\(\d+, \d+, \d+, \d+\)', f'filevers={version_tuple}', content)
        content = re.sub(r'prodvers=\(\d+, \d+, \d+, \d+\)', f'prodvers={version_tuple}', content)
        
        # Update StringStruct versions
        content = re.sub(r"StringStruct\(u'FileVersion', u'.*'\)", f"StringStruct(u'FileVersion', u'{final_version_string}')", content)
        content = re.sub(r"StringStruct\(u'ProductVersion', u'.*'\)", f"StringStruct(u'ProductVersion', u'{final_version_string}')", content)
        
        info_file.write_text(content, encoding='utf-8')
        print(f"Updated {info_file}")
    else:
        print(f"Warning: {info_file} not found")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        new_version = sys.argv[1]
    else:
        new_version = input("Enter new version (e.g., 1.5.0): ").strip()
        if not new_version:
            print("No version provided. Exiting.")
            sys.exit(1)
    
    update_version(new_version)
