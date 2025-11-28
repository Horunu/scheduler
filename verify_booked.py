#!/usr/bin/env python3
"""Verify a BOOKED room to show the difference"""
import requests
import json
from datetime import datetime, timedelta

# Room 18415 - De Morgan Group Study Pod (BOOKED)
room_id = 18415
location_id = '692'
group_id = '5421'
zone_id = '2246'

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Content-Type': 'application/x-www-form-urlencoded',
    'X-Requested-With': 'XMLHttpRequest'
})

room_url = f"https://library-calendars.ucl.ac.uk/space/{room_id}"
print(f"🌐 Checking BOOKED room: De Morgan Group Study Pod")
print(f"   URL: {room_url}\n")
session.get(room_url, timeout=10)
session.headers['Referer'] = room_url

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

response = session.post(
    'https://library-calendars.ucl.ac.uk/spaces/availability/grid',
    data=params,
    timeout=15
)

if response.status_code == 200:
    data = response.json()
    slots = data.get('slots', [])
    print(f"✅ API Response: {len(slots)} slots\n")

    for slot in slots:
        if '18:30' in slot.get('start', ''):
            print("🎯 Found 18:30 slot:")
            print(json.dumps(slot, indent=2))

            className = slot.get('className', '')
            if 's-lc-eq-avail' in className:
                print("\n✅ AVAILABLE")
            elif 's-lc-eq-checkout' in className:
                print("\n❌ BOOKED")
            elif not className:
                print("\n✅ AVAILABLE (no className)")
            else:
                print(f"\n⚠️  Other status: {className}")
            break
else:
    print(f"❌ Error: {response.status_code}")
