#!/usr/bin/env python3
"""
Process harvested relay data - USE the event types from the harvest!
The original harvest correctly extracted event types from the HTML sections.
"""

import json
import re
from pathlib import Path
from collections import defaultdict

INPUT_FILE = Path(__file__).parent / "harvested_relays" / "all_relays.json"
RECORDS_DIR = Path(__file__).parent / "records"

def parse_time_to_seconds(time_str):
    """Convert time string to total seconds."""
    parts = time_str.split(":")
    if len(parts) == 2:
        minutes = int(parts[0])
        seconds = float(parts[1])
        return minutes * 60 + seconds
    return float(time_str)

def get_relay_signature(swimmers, is_medley=False):
    """Get signature for deduplication."""
    if not swimmers or len(swimmers) < 4:
        return None
    normalized = [s.lower().strip() for s in swimmers[:4]]
    if is_medley:
        return tuple(normalized)
    else:
        return tuple(sorted(normalized))

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

def is_valid_relay_time(event, time_str):
    """Filter out obviously incorrect times."""
    seconds = parse_time_to_seconds(time_str)
    
    if event == "200 Free Relay":
        # 200 Free should be 1:25 - 2:30 (85-150 seconds)
        return 85 <= seconds <= 150
    elif event == "200 Medley Relay":
        # 200 Medley should be 1:45 - 2:45 (105-165 seconds)
        return 105 <= seconds <= 165
    elif event == "400 Free Relay":
        # 400 Free should be 3:15 - 6:00 (195-360 seconds)
        return 195 <= seconds <= 360
    
    return True

def process_relays(gender):
    """Process relays for a gender."""
    with open(INPUT_FILE) as f:
        data = json.load(f)
    
    relays = data.get(gender, [])
    print(f"\nProcessing {len(relays)} {gender} relay entries...")
    
    # Group by event type (from the harvest)
    classified = {"200 Medley Relay": [], "200 Free Relay": [], "400 Free Relay": []}
    
    skipped = 0
    for relay in relays:
        # Skip if no swimmers
        if not relay.get("swimmers") or len(relay["swimmers"]) < 4:
            continue
        
        # Use the event type from the harvest
        event = relay.get("event", "")
        
        # Normalize event names
        if "Medley" in event:
            event = "200 Medley Relay"
        elif "400" in event:
            event = "400 Free Relay"
        elif "200" in event or "Free" in event:
            event = "200 Free Relay"
        else:
            continue
        
        # Validate time is reasonable for the event
        if not is_valid_relay_time(event, relay["time"]):
            skipped += 1
            print(f"  Skipping invalid time: {relay['time']} for {event}")
            continue
        
        classified[event].append(relay)
    
    print(f"  Skipped {skipped} invalid times")
    
    # Sort by time within each event
    for event in classified:
        classified[event].sort(key=lambda x: parse_time_to_seconds(x["time"]))
    
    # Deduplicate (keep fastest time per unique swimmer combination)
    for event in classified:
        is_medley = "Medley" in event
        seen = set()
        deduped = []
        for relay in classified[event]:
            sig = get_relay_signature(relay["swimmers"], is_medley)
            if sig and sig not in seen:
                seen.add(sig)
                deduped.append(relay)
        classified[event] = deduped[:15]  # Top 15
    
    return classified

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
            swimmers_str = ", ".join(relay["swimmers"][:4])
            date_str = format_date(relay["date"])
            meet = relay["meet"]
            meet = re.sub(r'^Multi Teams @ ', '', meet)
            
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
    print("PROCESSING HARVESTED RELAY DATA (v3 - Using original event types)")
    print("=" * 60)
    
    for gender in ["girls", "boys"]:
        events = process_relays(gender)
        
        print(f"\n{gender.upper()} RESULTS:")
        for event, relays in events.items():
            print(f"  {event}: {len(relays)} unique relays")
            if relays:
                r = relays[0]
                print(f"    Best: {r['time']} - {', '.join(r['swimmers'][:4])}")
        
        markdown = generate_markdown(gender, events)
        output_file = RECORDS_DIR / f"relay-records-{gender}.md"
        
        with open(output_file, 'w') as f:
            f.write(markdown)
        
        print(f"\n  Saved to: {output_file}")
    
    print("\n" + "=" * 60)
    print("DONE! Now run: python3 generate_website.py")
    print("=" * 60)

if __name__ == "__main__":
    main()



