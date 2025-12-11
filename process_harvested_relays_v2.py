#!/usr/bin/env python3
"""
Process harvested relay data and properly categorize events.
Uses the original all_relays.json and re-categorizes based on time ranges
and meet context.
"""

import json
import re
from pathlib import Path
from collections import defaultdict
import subprocess

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

def classify_relay(relay, all_relays_for_meet):
    """
    Classify relay by event type based on time and context.
    
    Time ranges (approximate):
    - 200 Free Relay: 1:30 - 2:00 (fastest 200)
    - 200 Medley Relay: 1:50 - 2:20 (slower 200 due to stroke variety)
    - 400 Free Relay: 3:20 - 5:30 (longer distance)
    """
    seconds = parse_time_to_seconds(relay["time"])
    meet_relays = [r for r in all_relays_for_meet if parse_time_to_seconds(r["time"]) < 180]
    
    # Clear cases based on time
    if seconds > 180:  # Over 3:00 = 400 Free
        return "400 Free Relay"
    
    # For times under 3:00, we need to distinguish 200 Free vs 200 Medley
    # If there are multiple fast relays at a meet, the faster ones are likely 200 Free
    # and the slower ones are likely 200 Medley
    
    if seconds < 100:  # Under 1:40 - definitely 200 Free (very fast)
        return "200 Free Relay"
    
    if seconds > 130:  # Over 2:10 - likely 200 Medley or slower 200 Free
        return "200 Medley Relay"
    
    # 1:40 - 2:10 range - could be either
    # Use time relative to other relays at the same meet
    # Faster half = 200 Free, slower half = 200 Medley
    if len(meet_relays) >= 2:
        sorted_times = sorted([parse_time_to_seconds(r["time"]) for r in meet_relays])
        median = sorted_times[len(sorted_times) // 2]
        if seconds <= median:
            return "200 Free Relay"
        else:
            return "200 Medley Relay"
    
    # Default based on pure time
    if seconds < 115:  # Under 1:55
        return "200 Free Relay"
    else:
        return "200 Medley Relay"

def process_relays(gender):
    """Process relays for a gender."""
    with open(INPUT_FILE) as f:
        data = json.load(f)
    
    relays = data.get(gender, [])
    print(f"\nProcessing {len(relays)} {gender} relay entries...")
    
    # Group by meet for context
    by_meet = defaultdict(list)
    for relay in relays:
        if relay.get("swimmers") and len(relay["swimmers"]) >= 4:
            key = (relay.get("meet", ""), relay.get("date", ""))
            by_meet[key].append(relay)
    
    # Classify each relay
    classified = {"200 Medley Relay": [], "200 Free Relay": [], "400 Free Relay": []}
    
    for meet_key, meet_relays in by_meet.items():
        for relay in meet_relays:
            event = classify_relay(relay, meet_relays)
            relay["event"] = event
            classified[event].append(relay)
    
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
    print("PROCESSING HARVESTED RELAY DATA (v2)")
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



