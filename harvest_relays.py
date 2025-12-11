#!/usr/bin/env python3
"""
Harvest relay data from MaxPreps for Tanque Verde High School.
Iterates through seasons and meets to extract relay times and swimmers.
"""

import re
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime

# Seasons to harvest (format: YY-YY)
SEASONS = [
    "12-13", "13-14", "14-15", "15-16", "16-17", "17-18", "18-19", 
    "19-20", "20-21", "21-22", "22-23", "23-24", "24-25", "25-26"
]

GENDERS = ["girls", "boys"]

# Base URLs
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
    
    # Pattern to match full contest URLs
    pattern = r'https://www\.maxpreps\.com/local/contest/default\.aspx\?contestid=([a-f0-9-]+)&ssid=([a-f0-9-]+)'
    matches = re.findall(pattern, html)
    
    # Also try partial pattern
    if not matches:
        pattern2 = r'contestid=([a-f0-9-]+)&amp;ssid=([a-f0-9-]+)'
        matches = re.findall(pattern2, html)
    
    if not matches:
        pattern3 = r'contestid=([a-f0-9-]+)&ssid=([a-f0-9-]+)'
        matches = re.findall(pattern3, html)
    
    for contest_id, ssid in matches:
        contests.append({
            "contest_id": contest_id,
            "ssid": ssid,
            "url": f"https://www.maxpreps.com/local/contest/default.aspx?contestid={contest_id}&ssid={ssid}"
        })
    
    # Remove duplicates
    seen = set()
    unique = []
    for c in contests:
        key = c["contest_id"]
        if key not in seen:
            seen.add(key)
            unique.append(c)
    
    return unique

def extract_meet_info(html):
    """Extract meet name and date from contest page."""
    # Try to find meet name in h1
    meet_match = re.search(r'<h1[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</h1>', html)
    if not meet_match:
        meet_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
    meet_name = meet_match.group(1).strip() if meet_match else "Unknown Meet"
    
    # Clean up meet name
    meet_name = re.sub(r'\s+', ' ', meet_name)
    
    # Try to find date - look for pattern like "Fall 18-19 · 9/22/2018"
    date_match = re.search(r'·\s*(\d{1,2}/\d{1,2}/\d{4})', html)
    if date_match:
        meet_date = date_match.group(1)
    else:
        # Try other date patterns
        date_match2 = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', html)
        meet_date = date_match2.group(1) if date_match2 else "Unknown Date"
    
    return meet_name, meet_date

def extract_tanque_verde_relays(html, meet_name, meet_date, season):
    """Extract Tanque Verde relay results from contest page."""
    relays = []
    
    # Find all Tanque Verde relay entries
    # Pattern: Relay Team row with Tanque Verde school and ShowMedleySplitWindow
    
    # Pattern to match relay entries with swimmer names in onclick
    # ShowMedleySplitWindow(['Back','Breast','Fly','Free'],['Name1','Name2','Name3','Name4'],['time1','time2','time3','time4'],'Relay Team');
    
    relay_pattern = r"<td[^>]*class=\"place[^\"]*\"[^>]*>(\d+)(?:st|nd|rd|th)</td><td[^>]*class=\"name\"[^>]*>Relay Team</td><td[^>]*class=\"school\"[^>]*><a[^>]*tanque-verde[^>]*>[^<]*</a></td><td[^>]*class=\"round\"[^>]*>([^<]*)</td><td[^>]*class=\"splits\"[^>]*>([^<]*<input[^>]*onclick=\"([^\"]+)\"[^>]*/>[^<]*|[^<]*)</td><td[^>]*class=\"time[^\"]*\"[^>]*>(\d{1,2}:\d{2}\.\d{2})</td>"
    
    matches = re.findall(relay_pattern, html, re.IGNORECASE | re.DOTALL)
    
    for match in matches:
        place = match[0]
        round_name = match[1].strip()
        onclick = match[3] if len(match) > 3 else ""
        total_time = match[4] if len(match) > 4 else match[-1]
        
        # Extract swimmer names from onclick
        swimmers = []
        if onclick:
            # Pattern to extract swimmer names array
            names_match = re.search(r"ShowMedleySplitWindow\(\[[^\]]*\],\[([^\]]+)\]", onclick)
            if names_match:
                names_str = names_match.group(1)
                # Extract individual names
                swimmers = re.findall(r"'([^']+)'", names_str)
                # Remove duplicates (for 400 free where each swimmer appears twice)
                seen = set()
                unique_swimmers = []
                for s in swimmers:
                    if s not in seen:
                        seen.add(s)
                        unique_swimmers.append(s)
                swimmers = unique_swimmers
        
        relays.append({
            "place": place,
            "round": round_name,
            "time": total_time,
            "swimmers": swimmers,
            "meet": meet_name,
            "date": meet_date,
            "season": season
        })
    
    # Determine event type based on time
    for relay in relays:
        time_str = relay["time"]
        # Parse time to seconds for classification
        parts = time_str.split(":")
        if len(parts) == 2:
            minutes = int(parts[0])
            seconds = float(parts[1])
            total_seconds = minutes * 60 + seconds
            
            # Classify by time range
            if total_seconds < 140:  # Under 2:20
                relay["event"] = "200 Medley Relay"
            elif total_seconds < 160:  # Under 2:40  
                relay["event"] = "200 Free Relay"
            elif total_seconds < 280:  # Under 4:40
                relay["event"] = "200 Medley Relay" if "Back" in str(relay.get("onclick", "")) else "200 Free Relay"
            else:
                relay["event"] = "400 Free Relay"
    
    return relays

def identify_relay_event(html, relay_time, meet_section_start):
    """Try to identify the relay event from the HTML context."""
    # Look backwards from the relay entry to find the event header
    search_start = max(0, meet_section_start - 5000)
    context = html[search_start:meet_section_start]
    
    if "200 Medley" in context[-2000:]:
        return "200 Medley Relay"
    elif "200 Free Relay" in context[-2000:] or "200 Freestyle Relay" in context[-2000:]:
        return "200 Free Relay"
    elif "400 Free" in context[-2000:]:
        return "400 Free Relay"
    
    return None

def harvest_season(gender, season):
    """Harvest all relay data for a season."""
    print(f"\n{'='*60}")
    print(f"Harvesting {gender} {season}")
    print(f"{'='*60}")
    
    schedule_url = SCHEDULE_URL_TEMPLATE.format(gender=gender, season=season)
    print(f"Fetching schedule: {schedule_url}")
    
    html = fetch_url(schedule_url)
    if not html:
        print(f"  Failed to fetch schedule")
        return []
    
    if "Page Not Found" in html or "404" in html or len(html) < 1000:
        print(f"  Season not found or empty")
        return []
    
    contests = extract_contest_links(html)
    print(f"  Found {len(contests)} contests")
    
    all_relays = []
    
    for i, contest in enumerate(contests):
        print(f"  [{i+1}/{len(contests)}] Fetching: {contest['contest_id'][:8]}...")
        
        contest_html = fetch_url(contest["url"])
        if not contest_html:
            continue
        
        meet_name, meet_date = extract_meet_info(contest_html)
        print(f"    Meet: {meet_name} ({meet_date})")
        
        relays = extract_tanque_verde_relays(contest_html, meet_name, meet_date, season)
        if relays:
            print(f"    Found {len(relays)} relay entries:")
            for r in relays:
                swimmers_str = ", ".join(r["swimmers"][:4]) if r["swimmers"] else "No swimmers"
                print(f"      {r['time']} - {swimmers_str}")
            all_relays.extend(relays)
        
        # Be nice to the server
        time.sleep(0.5)
    
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
    output_file = OUTPUT_DIR / "all_relays.json"
    with open(output_file, 'w') as f:
        json.dump(all_data, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"HARVEST COMPLETE")
    print(f"{'='*60}")
    print(f"Girls relays: {len(all_data['girls'])}")
    print(f"Boys relays: {len(all_data['boys'])}")
    print(f"Data saved to: {output_file}")
    
    # Print summary
    for gender in GENDERS:
        print(f"\n{gender.upper()} TOP RELAYS BY TIME:")
        # Sort all relays by time
        sorted_relays = sorted(all_data[gender], key=lambda x: x["time"])
        for r in sorted_relays[:10]:
            swimmers = ", ".join(r["swimmers"][:4]) if r["swimmers"] else "Unknown"
            print(f"  {r['time']} - {swimmers} ({r['meet']}, {r['date']})")

if __name__ == "__main__":
    main()
