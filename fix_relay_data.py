#!/usr/bin/env python3
"""
Fix relay data quality issues:
1. Identify relays with fewer than 4 swimmers
2. Deduplicate relays:
   - Medley Relay: Same 4 swimmers in SAME ORDER = duplicate
   - 200 Free Relay: Same 4 swimmers in ANY ORDER = duplicate
   - 400 Free Relay: Same 4 swimmers in ANY ORDER = duplicate
"""

import re
import os
from pathlib import Path

RECORDS_DIR = Path(__file__).parent / "records"

def parse_relay_participants(participants_str):
    """Parse participant names from the relay string, stripping year info."""
    # Split by comma
    parts = [p.strip() for p in participants_str.split(',')]
    # Extract just the name (remove year designation like "(SR)", "(JR)", etc.)
    names = []
    for part in parts:
        # Remove year designation
        name = re.sub(r'\s*\([A-Z]{2}\)\s*$', '', part).strip()
        if name:
            names.append(name)
    return names

def normalize_name(name):
    """Normalize a name for comparison (lowercase, remove extra spaces)."""
    return ' '.join(name.lower().split())

def get_relay_signature(names, is_medley=False):
    """
    Get a signature for duplicate detection.
    For medley: order matters (return tuple in original order)
    For free relays: order doesn't matter (return sorted tuple)
    """
    normalized = [normalize_name(n) for n in names]
    if is_medley:
        return tuple(normalized)
    else:
        return tuple(sorted(normalized))

def process_relay_file(filepath):
    """Process a relay records file and fix data quality issues."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    lines = content.split('\n')
    new_lines = []
    
    current_event = None
    in_table = False
    header_lines = []
    data_rows = []
    
    warnings = []
    removed_duplicates = 0
    incomplete_relays = 0
    
    for i, line in enumerate(lines):
        # Detect event headers
        if line.startswith('## 200 Medley'):
            current_event = '200_medley'
        elif line.startswith('## 200 Free'):
            current_event = '200_free'
        elif line.startswith('## 400 Free'):
            current_event = '400_free'
        elif line.startswith('## '):
            current_event = None
        
        # Detect table start
        if '| Rank |' in line:
            in_table = True
            header_lines = [line]
            data_rows = []
            continue
        
        # Detect table separator
        if in_table and line.strip().startswith('|') and '-----' in line:
            header_lines.append(line)
            continue
        
        # Process table rows
        if in_table and line.strip().startswith('|') and '|' in line[1:]:
            data_rows.append(line)
            continue
        
        # End of table - process and output
        if in_table and (not line.strip().startswith('|') or line.strip() == ''):
            in_table = False
            
            # Process the collected table
            if current_event and data_rows:
                processed_rows, event_warnings, event_removed, event_incomplete = process_relay_table(
                    data_rows, current_event
                )
                warnings.extend(event_warnings)
                removed_duplicates += event_removed
                incomplete_relays += event_incomplete
                
                # Output header and processed rows
                for h in header_lines:
                    new_lines.append(h)
                for row in processed_rows:
                    new_lines.append(row)
            else:
                # Just output as-is
                for h in header_lines:
                    new_lines.append(h)
                for row in data_rows:
                    new_lines.append(row)
            
            header_lines = []
            data_rows = []
            new_lines.append(line)
            continue
        
        if not in_table:
            new_lines.append(line)
    
    # Handle case where file ends while in table
    if in_table and data_rows:
        if current_event:
            processed_rows, event_warnings, event_removed, event_incomplete = process_relay_table(
                data_rows, current_event
            )
            warnings.extend(event_warnings)
            removed_duplicates += event_removed
            incomplete_relays += event_incomplete
            
            for h in header_lines:
                new_lines.append(h)
            for row in processed_rows:
                new_lines.append(row)
        else:
            for h in header_lines:
                new_lines.append(h)
            for row in data_rows:
                new_lines.append(row)
    
    return '\n'.join(new_lines), warnings, removed_duplicates, incomplete_relays

def process_relay_table(rows, event_type):
    """Process relay table rows for duplicates and incomplete entries."""
    warnings = []
    removed = 0
    incomplete = 0
    
    is_medley = event_type == '200_medley'
    
    # Parse all rows
    parsed_rows = []
    for row in rows:
        parts = row.split('|')
        if len(parts) < 5:
            parsed_rows.append((row, None, None))
            continue
        
        # Extract participants (column 3, 0-indexed)
        participants_col = parts[3].strip() if len(parts) > 3 else ''
        
        # Remove bold markers
        participants_clean = participants_col.replace('**', '')
        
        # Parse names
        names = parse_relay_participants(participants_clean)
        
        if len(names) < 4:
            warnings.append(f"  Incomplete relay ({len(names)} swimmers): {participants_clean[:60]}...")
            incomplete += 1
        
        signature = get_relay_signature(names, is_medley) if len(names) >= 4 else None
        parsed_rows.append((row, names, signature))
    
    # Deduplicate - keep only the first (fastest) occurrence of each signature
    seen_signatures = set()
    deduped_rows = []
    
    for row, names, signature in parsed_rows:
        if signature is None:
            # Keep incomplete relays but flag them
            deduped_rows.append(row)
        elif signature in seen_signatures:
            removed += 1
            # Extract time for the warning
            parts = row.split('|')
            time_col = parts[2].strip().replace('**', '') if len(parts) > 2 else '?'
            warnings.append(f"  Removed duplicate relay: {time_col} - {', '.join(names[:4])}")
        else:
            seen_signatures.add(signature)
            deduped_rows.append(row)
    
    # Renumber ranks
    renumbered_rows = []
    rank = 1
    for row in deduped_rows:
        # Check if this is the record holder (bold row)
        is_record = '**' in row
        
        parts = row.split('|')
        if len(parts) >= 3:
            if is_record:
                parts[1] = f' **{rank}** '
            else:
                parts[1] = f' {rank} '
            row = '|'.join(parts)
            rank += 1
        
        renumbered_rows.append(row)
    
    return renumbered_rows, warnings, removed, incomplete

def main():
    print("=" * 60)
    print("RELAY DATA QUALITY FIXER")
    print("=" * 60)
    print()
    
    relay_files = [
        RECORDS_DIR / "relay-records-girls.md",
        RECORDS_DIR / "relay-records-boys.md"
    ]
    
    total_removed = 0
    total_incomplete = 0
    
    for filepath in relay_files:
        if not filepath.exists():
            print(f"File not found: {filepath}")
            continue
        
        print(f"Processing: {filepath.name}")
        print("-" * 40)
        
        new_content, warnings, removed, incomplete = process_relay_file(filepath)
        
        for w in warnings:
            print(w)
        
        if removed > 0 or incomplete > 0:
            print(f"  Summary: {removed} duplicates removed, {incomplete} incomplete relays found")
            
            # Write the updated file
            with open(filepath, 'w') as f:
                f.write(new_content)
            print(f"  Updated: {filepath}")
        else:
            print("  No changes needed")
        
        total_removed += removed
        total_incomplete += incomplete
        print()
    
    print("=" * 60)
    print(f"TOTAL: {total_removed} duplicates removed, {total_incomplete} incomplete relays flagged")
    print("=" * 60)

if __name__ == "__main__":
    main()



