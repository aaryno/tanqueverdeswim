#!/usr/bin/env python3
"""
Process harvested relay data with CORRECT time-based classification.

The harvester incorrectly labeled all relays - we must use time ranges.

Key insight: 200 FREE is ALWAYS faster than 200 MEDLEY because
free relay lets all 4 swimmers do freestyle (fastest stroke),
while medley requires back/breast/fly strokes which are slower.

Time ranges (based on actual high school swimming data):
GIRLS:
  - 200 Free Relay: 1:42 - 1:52 (fastest achievable 200)
  - 200 Medley Relay: 1:52 - 2:25 (10-15 sec slower due to stroke mix)
  - 400 Free Relay: 3:40 - 5:30

BOYS:
  - 200 Free Relay: 1:28 - 1:42 (fastest achievable 200)
  - 200 Medley Relay: 1:38 - 2:15 (8-12 sec slower)
  - 400 Free Relay: 3:15 - 4:30
"""

import json
import re
from pathlib import Path

INPUT_FILE = Path(__file__).parent / "harvested_relays" / "all_relays.json"
RECORDS_DIR = Path(__file__).parent / "records"

def parse_time_to_seconds(time_str):
    parts = time_str.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    return float(time_str)

def get_relay_signature(swimmers, is_medley=False):
    if not swimmers or len(swimmers) < 4:
        return None
    normalized = [s.lower().strip() for s in swimmers[:4]]
    if is_medley:
        return tuple(normalized)
    return tuple(sorted(normalized))

def format_date(date_str):
    import datetime
    try:
        parts = date_str.split("/")
        if len(parts) == 3:
            month, day, year = int(parts[0]), int(parts[1]), int(parts[2])
            return datetime.date(year, month, day).strftime("%b %d, %Y")
    except:
        pass
    return date_str

def classify_relay(relay, gender):
    """
    Classify relay by time. This is the ONLY reliable method since
    the harvester incorrectly labeled events.
    """
    seconds = parse_time_to_seconds(relay["time"])
    
    if gender == "girls":
        # Girls thresholds
        if seconds < 112:  # Under 1:52 = 200 Free (fastest)
            return "200 Free Relay"
        elif seconds < 145:  # 1:52 - 2:25 = 200 Medley
            return "200 Medley Relay"
        elif seconds >= 220:  # 3:40+ = 400 Free
            return "400 Free Relay"
        else:
            return None  # Invalid (2:25 - 3:40 gap)
    else:
        # Boys thresholds (faster than girls)
        if seconds < 102:  # Under 1:42 = 200 Free
            return "200 Free Relay"
        elif seconds < 135:  # 1:42 - 2:15 = 200 Medley
            return "200 Medley Relay"
        elif seconds >= 195:  # 3:15+ = 400 Free
            return "400 Free Relay"
        else:
            return None  # Invalid

def process_relays(gender):
    """Process relays for a gender."""
    with open(INPUT_FILE) as f:
        data = json.load(f)
    
    relays = data.get(gender, [])
    print(f"\nProcessing {len(relays)} {gender} relay entries...")
    
    classified = {"200 Medley Relay": [], "200 Free Relay": [], "400 Free Relay": []}
    skipped = 0
    
    for relay in relays:
        if not relay.get("swimmers") or len(relay["swimmers"]) < 4:
            continue
        
        event = classify_relay(relay, gender)
        if event:
            relay["classified_event"] = event
            classified[event].append(relay)
        else:
            skipped += 1
    
    print(f"  Skipped {skipped} relays with times in invalid ranges")
    
    # Sort each event by time
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
    title = "Girls" if gender == "girls" else "Boys"
    
    lines = [
        f"# {title} Relay Records",
        "## Tanque Verde High School Swimming",
        "",
        "---",
        ""
    ]
    
    for event_name in ["200 Medley Relay", "200 Free Relay", "400 Free Relay"]:
        relays = events.get(event_name, [])
        
        lines.append(f"## {event_name}")
        lines.append("")
        lines.append("| Rank | Time | Participants | Date | Meet |")
        lines.append("|-----:|-----:|--------------|------|------|")
        
        for i, relay in enumerate(relays, 1):
            swimmers_str = ", ".join(relay["swimmers"][:4])
            date_str = format_date(relay["date"])
            meet = re.sub(r'^Multi Teams @ ', '', relay["meet"])
            
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
    print("PROCESSING RELAYS (Correct Time-Based Classification)")
    print("=" * 60)
    
    for gender in ["girls", "boys"]:
        events = process_relays(gender)
        
        print(f"\n{gender.upper()} RESULTS:")
        for event, ev_relays in events.items():
            print(f"  {event}: {len(ev_relays)} unique relays")
            if ev_relays:
                r = ev_relays[0]
                print(f"    RECORD: {r['time']} - {', '.join(r['swimmers'][:4])}")
        
        markdown = generate_markdown(gender, events)
        output_file = RECORDS_DIR / f"relay-records-{gender}.md"
        
        with open(output_file, 'w') as f:
            f.write(markdown)
        
        print(f"  Saved to: {output_file}")
    
    print("\n" + "=" * 60)
    print("DONE!")
    print("=" * 60)

if __name__ == "__main__":
    main()



