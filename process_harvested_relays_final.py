#!/usr/bin/env python3
"""
Process harvested relay data with SMART time-based classification.
MaxPreps event labels are unreliable, so we classify based on time ranges.
"""

import json
import re
from pathlib import Path

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

def classify_relay_by_time(time_str, gender):
    """
    Classify relay by time. This is the most reliable method since
    MaxPreps event labels are unreliable.
    
    Time ranges based on typical high school relay times:
    
    GIRLS:
    - 200 Free Relay: 1:40 - 2:15 (fastest 200m events)
    - 200 Medley Relay: 2:00 - 2:45 (slightly slower due to strokes)
    - 400 Free Relay: 3:45 - 6:00 (longer distance)
    
    BOYS:
    - 200 Free Relay: 1:25 - 2:00 (fastest)
    - 200 Medley Relay: 1:45 - 2:30 (slower due to strokes)
    - 400 Free Relay: 3:15 - 4:45 (longer distance)
    
    Key insight: 
    - The FASTEST 200 relays are always 200 Free
    - 200 Medley is typically 10-15 seconds slower than 200 Free
    - 400 Free is roughly 2x the 200 Free time
    """
    seconds = parse_time_to_seconds(time_str)
    
    if gender == "girls":
        # Girls times
        if seconds < 120:  # Under 2:00 = 200 Free (fast)
            return "200 Free Relay"
        elif seconds < 170:  # 2:00 - 2:50 = 200 Medley (most 200s)
            return "200 Medley Relay"
        elif seconds >= 220 and seconds <= 400:  # 3:40 - 6:40 = 400 Free
            return "400 Free Relay"
        else:
            return None  # Invalid
    else:
        # Boys times (faster than girls)
        if seconds < 105:  # Under 1:45 = 200 Free (fast)
            return "200 Free Relay"
        elif seconds < 160:  # 1:45 - 2:40 = 200 Medley (most 200s)
            return "200 Medley Relay"
        elif seconds >= 195 and seconds <= 330:  # 3:15 - 5:30 = 400 Free
            return "400 Free Relay"
        else:
            return None  # Invalid

def process_relays(gender):
    """Process relays for a gender."""
    with open(INPUT_FILE) as f:
        data = json.load(f)
    
    relays = data.get(gender, [])
    print(f"\nProcessing {len(relays)} {gender} relay entries...")
    
    # Classify by time
    classified = {"200 Medley Relay": [], "200 Free Relay": [], "400 Free Relay": []}
    skipped = 0
    
    for relay in relays:
        if not relay.get("swimmers") or len(relay["swimmers"]) < 4:
            continue
        
        event = classify_relay_by_time(relay["time"], gender)
        if event:
            relay["event"] = event
            classified[event].append(relay)
        else:
            skipped += 1
    
    print(f"  Skipped {skipped} relays with invalid times")
    
    # Sort by time within each event
    for event in classified:
        classified[event].sort(key=lambda x: parse_time_to_seconds(x["time"]))
    
    # Deduplicate
    for event in classified:
        is_medley = "Medley" in event
        seen = set()
        deduped = []
        for relay in classified[event]:
            sig = get_relay_signature(relay["swimmers"], is_medley)
            if sig and sig not in seen:
                seen.add(sig)
                deduped.append(relay)
        classified[event] = deduped[:15]
    
    return classified

def generate_markdown(gender, events):
    """Generate markdown content for relay records."""
    title = "Girls" if gender == "girls" else "Boys"
    
    lines = [
        f"# {title} Relay Records",
        "## Tanque Verde High School Swimming",
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
    print("PROCESSING HARVESTED RELAY DATA (FINAL - Smart Time Classification)")
    print("=" * 60)
    
    for gender in ["girls", "boys"]:
        events = process_relays(gender)
        
        print(f"\n{gender.upper()} RESULTS:")
        for event, relays in events.items():
            print(f"  {event}: {len(relays)} unique relays")
            if relays:
                r = relays[0]
                print(f"    RECORD: {r['time']} - {', '.join(r['swimmers'][:4])}")
                print(f"            {r['meet'][:50]}... ({format_date(r['date'])})")
        
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



