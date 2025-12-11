#!/usr/bin/env python3
"""
Fix duplicate names in records by normalizing nicknames to full names.
"""

import os
import re
from pathlib import Path

# Name aliases - map nicknames to canonical full names
NAME_ALIASES = {
    "Nick Cusson": "Nicholas Cusson",
    "Nick Spilotro": "Nicholas Spilotro",
}

def fix_names_in_file(filepath: Path) -> int:
    """Fix name duplicates in a single file.
    
    Returns:
        Number of replacements made
    """
    with open(filepath, 'r') as f:
        content = f.read()
    
    original = content
    replacements = 0
    
    for nickname, fullname in NAME_ALIASES.items():
        # Count replacements
        count = content.count(nickname)
        if count > 0:
            content = content.replace(nickname, fullname)
            replacements += count
            print(f"  {filepath.name}: {nickname} → {fullname} ({count} times)")
    
    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
    
    return replacements


def main():
    records_dir = Path(__file__).parent / "records"
    
    if not records_dir.exists():
        print(f"Records directory not found: {records_dir}")
        return
    
    total_replacements = 0
    files_changed = 0
    
    print("Fixing name duplicates in records...")
    print("=" * 60)
    
    for md_file in sorted(records_dir.glob("*.md")):
        replacements = fix_names_in_file(md_file)
        if replacements > 0:
            files_changed += 1
            total_replacements += replacements
    
    print("=" * 60)
    print(f"Total: {total_replacements} replacements in {files_changed} files")


if __name__ == "__main__":
    main()



