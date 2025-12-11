#!/usr/bin/env python3
"""
Process harvested relay data and update relay records files.
"""

import json
import re
from pathlib import Path
from collections import defaultdict

INPUT_FILE = Path(__file__).parent / "harvested_relays" / "all_relays.json"
RECORDS_DIR = Path(__file__).parent / "records"

def parse_time_to_seconds(time_str):
    """Convert time string to total seconds for comparison."""
    parts = time_str.split(":")
    if len(parts) == 2:
        minutes = int(parts[0])
        seconds = float(parts[1])
        return minutes * 60 + seconds
    return float(time_str)

def classify_relay_event(time_str, swimmers=None):
    """Classify relay event based on time."""
    seconds = parse_time_to_seconds(time_str)
    
    # Time-based classification
    # 200 Medley: typically 1:40 - 2:20 (100-140 seconds)
    # 200 Free: typically 1:30 - 2:00 (90-120 seconds)
    # 400 Free: typically 3:20 - 5:30 (200-330 seconds)
    
    if seconds < 130:  # Under 2:10 - could be 200 Medley or 200 Free
        # Need context to distinguish, but we'll group by time range
        return "200 Relay"  # Will need manual review
    elif seconds < 200:  # 2:10 - 3:20
        return "200 Medley Relay"  # Slower 200s are usually medley
    elif seconds < 280:  # 3:20 - 4:40
        return "400 Free Relay"
    else:  # Over 4:40
        return "400 Free Relay"  # Slower 400s

def get_relay_signature(swimmers, is_medley=False):
    """Get signature for deduplication. For free relays, order doesn't matter."""
    if not swimmers or len(swimmers) < 4:
        return None
    
    # Normalize names
    normalized = [s.lower().strip() for s in swimmers[:4]]
    
    if is_medley:
        return tuple(normalized)  # Order matters
    else:
        return tuple(sorted(normalized))  # Order doesn't matter

def format_date(date_str):
    """Convert date from M/D/YYYY to Mon DD, YYYY format."""
    import datetime
    try:
        parts = date_str.split("/")
        if len(parts) == 3:
            month = int(parts[0])
            day = int(parts[1])
            year = int(parts[2])
            dt = datetime.date(year, month, day)
            return dt.strftime("%b %d, %Y")
    except:
        pass
    return date_str

def estimate_year(swimmers, season):
    """Estimate class year based on season and swimmer history."""
    # This is a simplified version - would need roster data for accuracy
    return ""

def process_relays(gender):
    """Process relays for a gender and create sorted/deduped lists."""
    with open(INPUT_FILE) as f:
        data = json.load(f)
    
    relays = data.get(gender, [])
    print(f"\nProcessing {len(relays)} {gender} relay entries...")
    
    # Group by approximate event type based on time
    fast_relays = []  # Under 2:00 - 200 Free Relay candidates
    medium_relays = []  # 2:00-3:00 - 200 Medley Relay candidates
    slow_relays = []  # Over 3:00 - 400 Free Relay
    
    for relay in relays:
        time_str = relay.get("time", "")
        if not time_str:
            continue
            
        seconds = parse_time_to_seconds(time_str)
        swimmers = relay.get("swimmers", [])
        
        # Skip entries without swimmers
        if not swimmers or len(swimmers) < 4:
            continue
        
        relay_entry = {
            "time": time_str,
            "seconds": seconds,
            "swimmers": swimmers[:4],
            "meet": relay.get("meet", "Unknown"),
            "date": relay.get("date", "Unknown"),
            "season": relay.get("season", ""),
            "round": relay.get("round", "")
        }
        
        if seconds < 120:  # Under 2:00
            fast_relays.append(relay_entry)
        elif seconds < 180:  # 2:00 - 3:00
            medium_relays.append(relay_entry)
        else:  # Over 3:00
            slow_relays.append(relay_entry)
    
    # Sort each group by time
    fast_relays.sort(key=lambda x: x["seconds"])
    medium_relays.sort(key=lambda x: x["seconds"])
    slow_relays.sort(key=lambda x: x["seconds"])
    
    # Deduplicate within each group
    def dedupe_relays(relay_list, is_medley=False):
        seen = set()
        deduped = []
        for relay in relay_list:
            sig = get_relay_signature(relay["swimmers"], is_medley)
            if sig and sig not in seen:
                seen.add(sig)
                deduped.append(relay)
        return deduped
    
    # 200 Free Relay (fast) - order doesn't matter
    fast_deduped = dedupe_relays(fast_relays, is_medley=False)
    
    # 200 Medley Relay (medium) - order matters
    medium_deduped = dedupe_relays(medium_relays, is_medley=True)
    
    # 400 Free Relay (slow) - order doesn't matter
    slow_deduped = dedupe_relays(slow_relays, is_medley=False)
    
    return {
        "200 Free Relay": fast_deduped[:15],  # Top 15
        "200 Medley Relay": medium_deduped[:15],
        "400 Free Relay": slow_deduped[:15]
    }

def generate_markdown(gender, events):
    """Generate markdown content for relay records."""
    title = "Girls" if gender == "girls" else "Boys"
    
    lines = [
        f"# {title} Relay Records",
        "## Tanque Verde High School Swimming",
        "",
        f"**Generated:** December 1, 2025",
        "",
        "---",
        ""
    ]
    
    event_order = ["200 Medley Relay", "200 Free Relay", "400 Free Relay"]
    
    for event_name in event_order:
        relays = events.get(event_name, [])
        
        lines.append(f"## {event_name}")
        lines.append("")
        lines.append("| Rank | Time | Participants | Date | Meet |")
        lines.append("|-----:|-----:|--------------|------|------|")
        
        for i, relay in enumerate(relays, 1):
            # Format swimmers
            swimmers_str = ", ".join(relay["swimmers"])
            
            # Format date
            date_str = format_date(relay["date"])
            
            # Format meet name (clean up)
            meet = relay["meet"]
            meet = re.sub(r'^Multi Teams @ ', '', meet)
            
            # Bold the record holder (rank 1)
            if i == 1:
                lines.append(f"| **{i}** | **{relay['time']}** | **{swimmers_str}** | **{date_str}** | **{meet}** |")
            else:
                lines.append(f"| {i} | {relay['time']} | {swimmers_str} | {date_str} | {meet} |")
        
        lines.append("")
        lines.append("---")
        lines.append("")
    
    return "\n".join(lines)

def main():
    print("=" * 60)
    print("PROCESSING HARVESTED RELAY DATA")
    print("=" * 60)
    
    for gender in ["girls", "boys"]:
        events = process_relays(gender)
        
        print(f"\n{gender.upper()} RESULTS:")
        for event, relays in events.items():
            print(f"  {event}: {len(relays)} unique relays")
            if relays:
                print(f"    Best: {relays[0]['time']} - {', '.join(relays[0]['swimmers'][:4])}")
        
        # Generate and save markdown
        markdown = generate_markdown(gender, events)
        output_file = RECORDS_DIR / f"relay-records-{gender}.md"
        
        with open(output_file, 'w') as f:
            f.write(markdown)
        
        print(f"\n  Saved to: {output_file}")
    
    print("\n" + "=" * 60)
    print("DONE!")
    print("=" * 60)

if __name__ == "__main__":
    main()



