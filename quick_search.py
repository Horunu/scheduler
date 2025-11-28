#!/usr/bin/env python3
"""
Quick room search for specific criteria
"""

import json
import sys

def quick_search(num_people, location_filter=""):
    # Load cached room data
    try:
        with open("ucl_rooms.json", 'r') as f:
            all_rooms = json.load(f)
    except:
        print("❌ Room data not found. Run: python3 ucl_scraper.py")
        return

    # Deduplicate
    unique_rooms = {}
    for room in all_rooms:
        room_id = room['id']
        if room_id not in unique_rooms:
            unique_rooms[room_id] = room
        elif room['zone_id'] != '0' and unique_rooms[room_id]['zone_id'] == '0':
            unique_rooms[room_id] = room

    rooms = list(unique_rooms.values())

    # Filter
    filtered = [r for r in rooms if r['capacity'] >= num_people]

    if location_filter:
        filtered = [r for r in filtered if location_filter.lower() in r['location_name'].lower()]

    # Sort: smallest capacity first, prefer specific room types
    filtered.sort(key=lambda r: (r['capacity'], r['name']))

    # Display top results
    print(f"\n🔍 Best matches for {num_people} people:")
    print("=" * 90)

    shown = 0
    for room in filtered[:15]:  # Top 15
        shown += 1
        print(f"\n{shown}. {room['name']}")
        print(f"   👥 {room['capacity']} people | 📍 {room['location_name']}")
        print(f"   🏢 {room['zone_name']} | 📂 {room['group_name']}")
        print(f"   🔗 {room['booking_url']}")

    print("\n" + "=" * 90)
    print(f"Showing top {shown} of {len(filtered)} total matches")
    print("\n💡 Click the links above to check live availability for 18:30 today!")
    print()

if __name__ == "__main__":
    num_people = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    location = sys.argv[2] if len(sys.argv) > 2 else ""
    quick_search(num_people, location)
