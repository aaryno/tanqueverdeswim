#!/usr/bin/env python3
"""
Harvest relay data from MaxPreps for Tanque Verde High School.
Version 2: Properly extracts event type from HTML context.
"""

import re
import json
import time
import subprocess
from pathlib import Path

SEASONS = [
    "12-13", "13-14", "14-15", "15-16", "16-17", "17-18", "18-19", 
    "19-20", "20-21", "21-22", "22-23", "23-24", "24-25", "25-26"
]

GENDERS = ["girls", "boys"]
SCHEDULE_URL_TEMPLATE = "https://www.maxpreps.com/az/tucson/tanque-verde-hawks/swimming/{gender}/fall/{season}/schedule/"
OUTPUT_DIR = Path(__file__).parent / "harvested_relays"

def fetch_url(url):
    """Fetch URL content using curl."""
    cmd = [
        "curl", "-s", "-L",
        "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        url
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return None

def extract_contest_links(html):
    """Extract contest URLs from schedule page."""
    contests = []
    patterns = [
        r'contestid=([a-f0-9-]+)&amp;ssid=([a-f0-9-]+)',
        r'contestid=([a-f0-9-]+)&ssid=([a-f0-9-]+)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, html)
        for contest_id, ssid in matches:
            contests.append({
                "contest_id": contest_id,
                "ssid": ssid,
                "url": f"https://www.maxpreps.com/local/contest/default.aspx?contestid={contest_id}&ssid={ssid}"
            })
    
    seen = set()
    unique = []
    for c in contests:
        if c["contest_id"] not in seen:
            seen.add(c["contest_id"])
            unique.append(c)
    return unique

def extract_meet_info(html):
    """Extract meet name and date from contest page."""
    meet_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
    meet_name = meet_match.group(1).strip() if meet_match else "Unknown Meet"
    meet_name = re.sub(r'\s+', ' ', meet_name)
    
    date_match = re.search(r'·\s*(\d{1,2}/\d{1,2}/\d{4})', html)
    if not date_match:
        date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', html)
    meet_date = date_match.group(1) if date_match else "Unknown Date"
    
    return meet_name, meet_date

def extract_relays_by_event(html, meet_name, meet_date, season):
    """Extract Tanque Verde relay results organized by event type."""
    relays = []
    
    # Define event patterns to search for
    events = [
        ("200 Medley Relay", r"200\s*Medley\s*Relay"),
        ("200 Free Relay", r"200\s*Free(?:style)?\s*Relay"),
        ("400 Free Relay", r"400\s*Free(?:style)?\s*Relay")
    ]
    
    for event_name, event_pattern in events:
        # Find the section for this event
        event_match = re.search(event_pattern, html, re.IGNORECASE)
        if not event_match:
            continue
        
        start_pos = event_match.start()
        
        # Find the next event or end of relays section
        end_pos = len(html)
        for other_event, other_pattern in events:
            if other_event != event_name:
                other_match = re.search(other_pattern, html[start_pos + 50:], re.IGNORECASE)
                if other_match:
                    potential_end = start_pos + 50 + other_match.start()
                    if potential_end < end_pos:
                        end_pos = potential_end
        
        # Also look for "About Us" or other page endings
        about_match = html.find("About Us", start_pos)
        if about_match != -1 and about_match < end_pos:
            end_pos = about_match
        
        section_html = html[start_pos:end_pos]
        
        # Find all Tanque Verde relay entries in this section
        # Pattern: Relay Team with tanque-verde and ShowMedleySplitWindow
        relay_pattern = r'<td[^>]*class="place[^"]*"[^>]*>(\d+)(?:st|nd|rd|th)</td>\s*<td[^>]*class="name"[^>]*>Relay Team</td>\s*<td[^>]*class="school"[^>]*><a[^>]*tanque-verde[^>]*>[^<]*</a></td>\s*<td[^>]*class="round"[^>]*>([^<]*)</td>\s*<td[^>]*class="splits"[^>]*>([^<]*(?:<input[^>]*onclick="([^"]*)"[^>]*/>)?[^<]*)</td>\s*<td[^>]*class="time[^"]*"[^>]*>(\d{1,2}:\d{2}\.\d{2})</td>'
        
        matches = re.findall(relay_pattern, section_html, re.IGNORECASE | re.DOTALL)
        
        for match in matches:
            place = match[0]
            round_name = match[1].strip()
            onclick = match[3] if len(match) > 3 else ""
            total_time = match[4] if len(match) > 4 else match[-1]
            
            # Extract swimmer names from onclick
            swimmers = []
            if onclick:
                # Pattern: ShowMedleySplitWindow([legs], [names], [times], ...)
                names_match = re.search(r"ShowMedleySplitWindow\(\[[^\]]*\],\[([^\]]+)\]", onclick)
                if names_match:
                    names_str = names_match.group(1)
                    swimmers = re.findall(r"'([^']+)'", names_str)
                    # Dedupe for 400 free where swimmers appear twice
                    seen = []
                    for s in swimmers:
                        if s not in seen:
                            seen.append(s)
                    swimmers = seen[:4]
            
            if swimmers and len(swimmers) >= 4:
                relays.append({
                    "event": event_name,
                    "place": place,
                    "round": round_name,
                    "time": total_time,
                    "swimmers": swimmers[:4],
                    "meet": meet_name,
                    "date": meet_date,
                    "season": season
                })
    
    return relays

def harvest_season(gender, season):
    """Harvest all relay data for a season."""
    print(f"\n{'='*60}")
    print(f"Harvesting {gender} {season}")
    print(f"{'='*60}")
    
    schedule_url = SCHEDULE_URL_TEMPLATE.format(gender=gender, season=season)
    html = fetch_url(schedule_url)
    
    if not html or "Page Not Found" in html or len(html) < 1000:
        print(f"  Season not found")
        return []
    
    contests = extract_contest_links(html)
    print(f"  Found {len(contests)} contests")
    
    all_relays = []
    
    for i, contest in enumerate(contests):
        print(f"  [{i+1}/{len(contests)}] Fetching...")
        
        contest_html = fetch_url(contest["url"])
        if not contest_html:
            continue
        
        meet_name, meet_date = extract_meet_info(contest_html)
        relays = extract_relays_by_event(contest_html, meet_name, meet_date, season)
        
        if relays:
            print(f"    {meet_name}: {len(relays)} relays")
            for r in relays:
                print(f"      {r['event']}: {r['time']} - {', '.join(r['swimmers'][:2])}...")
            all_relays.extend(relays)
        
        time.sleep(0.3)
    
    return all_relays

def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    all_data = {"girls": [], "boys": []}
    
    for gender in GENDERS:
        for season in SEASONS:
            relays = harvest_season(gender, season)
            for relay in relays:
                relay["gender"] = gender
            all_data[gender].extend(relays)
    
    # Save raw data
    output_file = OUTPUT_DIR / "all_relays_v2.json"
    with open(output_file, 'w') as f:
        json.dump(all_data, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"HARVEST COMPLETE")
    print(f"{'='*60}")
    
    for gender in GENDERS:
        print(f"\n{gender.upper()}:")
        events = {}
        for r in all_data[gender]:
            event = r.get("event", "Unknown")
            if event not in events:
                events[event] = []
            events[event].append(r)
        
        for event, relays in sorted(events.items()):
            relays.sort(key=lambda x: x["time"])
            print(f"  {event}: {len(relays)} entries")
            if relays:
                print(f"    Best: {relays[0]['time']} - {', '.join(relays[0]['swimmers'][:4])}")
    
    print(f"\nData saved to: {output_file}")

if __name__ == "__main__":
    main()



