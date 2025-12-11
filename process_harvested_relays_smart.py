#!/usr/bin/env python3
"""
Process harvested relay data with SMART classification.
Uses same-swimmer detection to distinguish 200 Free from 200 Medley.
"""

import json
import re
from pathlib import Path
from collections import defaultdict

INPUT_FILE = Path(__file__).parent / "harvested_relays" / "all_relays.json"
RECORDS_DIR = Path(__file__).parent / "records"

def parse_time_to_seconds(time_str):
    parts = time_str.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    return float(time_str)

def get_relay_signature(swimmers):
    """Get normalized signature (order-independent)."""
    if not swimmers or len(swimmers) < 4:
        return None
    return tuple(sorted([s.lower().strip() for s in swimmers[:4]]))

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

def classify_relays(relays, gender):
    """
    Classify relays using time ranges and same-swimmer detection.
    
    Strategy:
    1. Clear 400 Free: times 3:00+ 
    2. Clear 200 Free: times under 1:50 (girls) or 1:38 (boys)
    3. Clear 200 Medley: times 2:00+ (but under 3:00)
    4. Overlap zone (1:50-2:00 for girls, 1:38-2:00 for boys):
       - If same swimmers have both a fast and slow time, fast=Free, slow=Medley
       - Otherwise use median: below median = Free, above = Medley
    """
    classified = {"200 Medley Relay": [], "200 Free Relay": [], "400 Free Relay": []}
    overlap_zone = []
    
    # First pass: classify obvious cases
    for relay in relays:
        if not relay.get("swimmers") or len(relay["swimmers"]) < 4:
            continue
            
        seconds = parse_time_to_seconds(relay["time"])
        
        if seconds >= 200:  # 3:20+ = 400 Free
            classified["400 Free Relay"].append(relay)
        elif gender == "girls":
            if seconds < 110:  # Under 1:50 = 200 Free
                classified["200 Free Relay"].append(relay)
            elif seconds >= 120:  # 2:00+ = 200 Medley
                classified["200 Medley Relay"].append(relay)
            else:  # 1:50 - 2:00 overlap
                overlap_zone.append(relay)
        else:  # boys
            if seconds < 98:  # Under 1:38 = 200 Free
                classified["200 Free Relay"].append(relay)
            elif seconds >= 110:  # 1:50+ = 200 Medley
                classified["200 Medley Relay"].append(relay)
            else:  # 1:38 - 1:50 overlap
                overlap_zone.append(relay)
    
    # Second pass: classify overlap zone using same-swimmer detection
    if overlap_zone:
        # Group by swimmer signature
        by_sig = defaultdict(list)
        for relay in overlap_zone:
            sig = get_relay_signature(relay["swimmers"])
            if sig:
                by_sig[sig].append(relay)
        
        # Also check what's already classified
        free_sigs = set()
        medley_sigs = set()
        for relay in classified["200 Free Relay"]:
            sig = get_relay_signature(relay["swimmers"])
            if sig:
                free_sigs.add(sig)
        for relay in classified["200 Medley Relay"]:
            sig = get_relay_signature(relay["swimmers"])
            if sig:
                medley_sigs.add(sig)
        
        for relay in overlap_zone:
            sig = get_relay_signature(relay["swimmers"])
            seconds = parse_time_to_seconds(relay["time"])
            
            # If these swimmers already have a 200 Free, this is 200 Medley
            if sig in free_sigs:
                classified["200 Medley Relay"].append(relay)
            # If these swimmers already have a 200 Medley, this is 200 Free
            elif sig in medley_sigs:
                classified["200 Free Relay"].append(relay)
            else:
                # Use median of overlap zone
                times = [parse_time_to_seconds(r["time"]) for r in overlap_zone]
                median = sorted(times)[len(times) // 2] if times else 115
                if seconds < median:
                    classified["200 Free Relay"].append(relay)
                else:
                    classified["200 Medley Relay"].append(relay)
    
    # Sort each event by time
    for event in classified:
        classified[event].sort(key=lambda x: parse_time_to_seconds(x["time"]))
    
    # Deduplicate (keep fastest per unique swimmer combo)
    for event in classified:
        is_medley = "Medley" in event
        seen = set()
        deduped = []
        for relay in classified[event]:
            if is_medley:
                sig = tuple([s.lower().strip() for s in relay["swimmers"][:4]])
            else:
                sig = get_relay_signature(relay["swimmers"])
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
    print("PROCESSING HARVESTED RELAY DATA (Smart Classification)")
    print("=" * 60)
    
    with open(INPUT_FILE) as f:
        data = json.load(f)
    
    for gender in ["girls", "boys"]:
        relays = data.get(gender, [])
        print(f"\nProcessing {len(relays)} {gender} relay entries...")
        
        events = classify_relays(relays, gender)
        
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



