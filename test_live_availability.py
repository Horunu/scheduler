#!/usr/bin/env python3
"""
Quick test: Check actual availability for specific rooms at 18:30 today
"""

import requests
import json
from datetime import datetime

# Test rooms from our results
test_rooms = [
    {"id": 18407, "name": "Cruciform Hub - Hilton Study Room", "lid": "1140"},
    {"id": 29187, "name": "IOE Library - Group Study Pod E", "lid": "1143"},
    {"id": 21641, "name": "Royal Free - Study Pod A", "lid": "1778"},
]

date = "2025-11-28"
target_time = "18:30"

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest'
})

print(f"🔍 Checking availability for {date} at {target_time}\n")
print("=" * 80)

for room in test_rooms:
    print(f"\n📍 {room['name']} (ID: {room['id']})")

    # Try to visit the room page first to get cookies
    try:
        room_url = f"https://library-calendars.ucl.ac.uk/spaces?lid={room['id']}"
        session.get(room_url, timeout=10)
    except:
        pass

    # Try the availability endpoint with different parameter combinations
    endpoints = [
        f"https://library-calendars.ucl.ac.uk/spaces/availability/grid",
        f"https://library-calendars.ucl.ac.uk/availability",
        f"https://library-calendars.ucl.ac.uk/space/{room['id']}/availability"
    ]

    for endpoint in endpoints:
        try:
            # Try GET with params
            params = {
                'eid': room['id'],
                'lid': room['lid'],
                'date': date,
                'start': date,
                'end': date
            }

            response = session.get(endpoint, params=params, timeout=10)

            if response.status_code == 200:
                try:
                    data = response.json()
                    if data:
                        print(f"   ✅ Got data from: {endpoint}")
                        print(f"   Response keys: {list(data.keys())[:5]}")

                        # Look for availability info
                        if 'slots' in data:
                            slots = data['slots']
                            print(f"   Found {len(slots)} time slots")

                            # Check 18:30
                            for slot in slots:
                                if '18:30' in str(slot.get('start', '')):
                                    avail = 'AVAILABLE' if 's-lc-eq-avail' in slot.get('className', '') else 'BOOKED'
                                    print(f"   🕐 18:30 status: {avail}")
                                    break
                        break
                except:
                    pass

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                continue  # Try next endpoint
        except:
            continue

print("\n" + "=" * 80)
print("\n💡 Note: If no availability data shown, the API requires authentication")
print("   Users should click the booking links to see live availability\n")
