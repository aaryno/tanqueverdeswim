#!/usr/bin/env python3
"""
Fix data quality issues in TVHS swim records:
1. Normalize name variations (Sam Stott -> Samuel Stott)
2. Deduplicate swimmers in Top 10 lists (keep fastest time, or earliest if tied)
3. Re-number rankings after deduplication
"""

import re
from pathlib import Path
from datetime import datetime

# Name aliases - map variations to canonical names
NAME_FIXES = {
    "Sam Stott": "Samuel Stott",
}


def parse_time_to_seconds(time_str: str) -> float:
    """Convert swim time string to seconds for comparison."""
    time_str = time_str.strip()
    if ':' in time_str:
        parts = time_str.split(':')
        if len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    return float(time_str)


def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime for comparison."""
    date_str = date_str.strip()
    try:
        return datetime.strptime(date_str, "%b %d, %Y")
    except ValueError:
        return datetime.max


def fix_names_in_file(filepath: Path) -> int:
    """Fix name variations in a file."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    original = content
    fixes = 0
    
    for old_name, new_name in NAME_FIXES.items():
        count = content.count(old_name)
        if count > 0:
            content = content.replace(old_name, new_name)
            fixes += count
            print(f"  {filepath.name}: {old_name} → {new_name} ({count}x)")
    
    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
    
    return fixes


def deduplicate_top10(filepath: Path) -> int:
    """Deduplicate swimmers in top10 file - keep fastest time per swimmer per event."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    lines = content.split('\n')
    new_lines = []
    removals = 0
    
    in_table = False
    seen_swimmers = set()  # Track swimmers seen in current event
    
    for line in lines:
        # Detect new event section (resets seen swimmers)
        if line.startswith('##') or line.startswith('### '):
            in_table = False
            seen_swimmers = set()
            new_lines.append(line)
            continue
        
        # Detect table header
        if '| Rank |' in line or '|-----' in line:
            in_table = True
            new_lines.append(line)
            continue
        
        # Detect table end
        if in_table and line.strip() == '':
            in_table = False
            seen_swimmers = set()
            new_lines.append(line)
            continue
        
        # Process data rows
        if in_table and line.strip().startswith('|') and '|' in line[1:]:
            # Parse the row: | Rank | Time | Athlete | Year | Date | Meet |
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 5:
                # parts[0] is empty (before first |)
                # parts[1] is rank, parts[2] is time, parts[3] is athlete
                athlete = parts[3] if len(parts) > 3 else ""
                
                if athlete and athlete not in seen_swimmers:
                    seen_swimmers.add(athlete)
                    new_lines.append(line)
                elif athlete:
                    # Duplicate swimmer - skip this line
                    removals += 1
                    print(f"  {filepath.name}: Removed duplicate {athlete}")
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    if removals > 0:
        with open(filepath, 'w') as f:
            f.write('\n'.join(new_lines))
    
    return removals


def renumber_rankings(filepath: Path) -> int:
    """Re-number rankings after removing duplicate lines."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    lines = content.split('\n')
    new_lines = []
    changes = 0
    current_rank = 0
    in_table = False
    
    for line in lines:
        # Detect table start (header row)
        if '| Rank |' in line:
            in_table = True
            current_rank = 0
            new_lines.append(line)
            continue
        
        # Detect separator line
        if in_table and line.strip().startswith('|--'):
            new_lines.append(line)
            continue
        
        # Detect table end (blank line or new section)
        if in_table and (line.strip() == '' or line.startswith('#')):
            in_table = False
            current_rank = 0
            new_lines.append(line)
            continue
        
        # Process data rows
        if in_table and line.strip().startswith('|'):
            current_rank += 1
            # Replace the rank number
            match = re.match(r'\|\s*(\d+)\s*\|', line)
            if match:
                old_rank = int(match.group(1))
                if old_rank != current_rank:
                    line = re.sub(r'\|\s*\d+\s*\|', f'| {current_rank} |', line, count=1)
                    changes += 1
        
        new_lines.append(line)
    
    if changes > 0:
        with open(filepath, 'w') as f:
            f.write('\n'.join(new_lines))
    
    return changes


def main():
    records_dir = Path(__file__).parent / "records"
    
    if not records_dir.exists():
        print(f"Records directory not found: {records_dir}")
        return
    
    print("=" * 60)
    print("STEP 1: Fixing name variations...")
    print("=" * 60)
    
    total_name_fixes = 0
    for md_file in sorted(records_dir.glob("*.md")):
        fixes = fix_names_in_file(md_file)
        total_name_fixes += fixes
    
    print(f"\nTotal name fixes: {total_name_fixes}")
    
    print("\n" + "=" * 60)
    print("STEP 2: Deduplicating swimmers in Top 10 files...")
    print("=" * 60)
    
    total_removals = 0
    for md_file in sorted(records_dir.glob("top10*.md")):
        removals = deduplicate_top10(md_file)
        total_removals += removals
    
    print(f"\nTotal duplicates removed: {total_removals}")
    
    print("\n" + "=" * 60)
    print("STEP 3: Re-numbering rankings...")
    print("=" * 60)
    
    total_renumbered = 0
    for md_file in sorted(records_dir.glob("top10*.md")):
        renumbered = renumber_rankings(md_file)
        if renumbered > 0:
            print(f"  {md_file.name}: Re-numbered {renumbered} rankings")
        total_renumbered += renumbered
    
    print(f"\nTotal rankings renumbered: {total_renumbered}")
    
    print("\n" + "=" * 60)
    print("DONE!")
    print("=" * 60)


if __name__ == "__main__":
    main()
