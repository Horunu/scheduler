#!/usr/bin/env python3
"""Quick verification script to show raw API data for a specific room"""
import requests
import json
from datetime import datetime, timedelta

# Room 29187 - IOE Library - Group Study Pod E
room_id = 29187
location_id = '1143'
group_id = '2530'
zone_id = '355'

# Setup session
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Content-Type': 'application/x-www-form-urlencoded',
    'X-Requested-With': 'XMLHttpRequest'
})

# Visit room page first (establish session)
room_url = f"https://library-calendars.ucl.ac.uk/space/{room_id}"
print(f"🌐 Visiting: {room_url}")
session.get(room_url, timeout=10)

# Set referer for API call
session.headers['Referer'] = room_url

# Query API
date = datetime.now().strftime('%Y-%m-%d')
end_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

params = {
    'lid': location_id,
    'gid': group_id,
    'eid': room_id,
    'seat': 0,
    'seatId': 0,
    'zone': zone_id,
    'filters': '[]',
    'start': date,
    'end': end_date,
    'bookings': '[]',
    'pageIndex': 0,
    'pageSize': 100
}

print(f"📡 Querying API for {date}...\n")
response = session.post(
    'https://library-calendars.ucl.ac.uk/spaces/availability/grid',
    data=params,
    timeout=15
)

if response.status_code == 200:
    data = response.json()
    slots = data.get('slots', [])

    print(f"✅ API Response: {len(slots)} slots returned\n")

    # Find 18:30 slot
    for slot in slots:
        if '18:30' in slot.get('start', ''):
            print("🎯 Found 18:30 slot:")
            print(json.dumps(slot, indent=2))

            # Interpret status
            className = slot.get('className', '')
            if 's-lc-eq-avail' in className:
                print("\n✅ STATUS: AVAILABLE (green)")
            elif 's-lc-eq-checkout' in className:
                print("\n❌ STATUS: BOOKED (red)")
            else:
                print(f"\n⚠️  STATUS: {className}")
            break
else:
    print(f"❌ API Error: {response.status_code}")
    print(response.text[:500])
