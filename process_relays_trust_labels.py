#!/usr/bin/env python3
"""
Process harvested relay data - trust the original event labels from MaxPreps.
Only override for clearly misclassified times (like 400s labeled as 200s).
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
    """Get normalized signature."""
    if not swimmers or len(swimmers) < 4:
        return None
    normalized = [s.lower().strip() for s in swimmers[:4]]
    if is_medley:
        return tuple(normalized)  # Order matters for medley
    return tuple(sorted(normalized))  # Order doesn't matter for free

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

def classify_relay(relay):
    """
    Classify relay - trust the original label but fix obvious errors.
    """
    orig_event = relay.get("event", "")
    seconds = parse_time_to_seconds(relay["time"])
    
    # Fix obvious misclassifications based on time
    if seconds >= 200:  # Over 3:20 is always 400 Free
        return "400 Free Relay"
    
    # For times under 3:20, trust the original label
    if "Medley" in orig_event:
        return "200 Medley Relay"
    elif "400" in orig_event:
        # This is a misclassification - 400 can't be under 3:20
        # Classify based on time
        if seconds < 130:  # Under 2:10
            return "200 Free Relay"
        else:
            return "200 Medley Relay"
    else:  # 200 Free or just "Free"
        return "200 Free Relay"

def process_relays(gender):
    """Process relays for a gender."""
    with open(INPUT_FILE) as f:
        data = json.load(f)
    
    relays = data.get(gender, [])
    print(f"\nProcessing {len(relays)} {gender} relay entries...")
    
    classified = {"200 Medley Relay": [], "200 Free Relay": [], "400 Free Relay": []}
    
    for relay in relays:
        if not relay.get("swimmers") or len(relay["swimmers"]) < 4:
            continue
        
        event = classify_relay(relay)
        relay["classified_event"] = event
        classified[event].append(relay)
    
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
    print("PROCESSING RELAYS (Trust Original Labels)")
    print("=" * 60)
    
    with open(INPUT_FILE) as f:
        data = json.load(f)
    
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



