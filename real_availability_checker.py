#!/usr/bin/env python3
"""
Real Availability Checker - Directly queries the availability API
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RealAvailabilityChecker:
    """Queries UCL's availability API directly"""

    BASE_URL = "https://library-calendars.ucl.ac.uk"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
            'X-Requested-With': 'XMLHttpRequest',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        })

    def get_room_availability(self, room_id: int, date: str) -> Optional[Dict]:
        """
        Get availability data for a specific room

        Returns dict with 'slots' array containing availability info
        """
        # First visit the room page to establish session and get cookies
        room_url = f"{self.BASE_URL}/spaces?lid={room_id}"

        try:
            # Visit room page
            page_response = self.session.get(room_url, timeout=15)
            page_response.raise_for_status()

            # Small delay
            time.sleep(0.5)

            # Now try the availability endpoint
            avail_url = f"{self.BASE_URL}/spaces/availability/grid"

            # Try different parameter combinations
            param_sets = [
                {
                    'eid': room_id,
                    'gid': 0,
                    'lid': room_id,
                    'start': date,
                    'end': date,
                },
                {
                    'eid[]': room_id,
                    'date': date,
                },
                {
                    'lid': room_id,
                    'start': date,
                    'end': date,
                }
            ]

            for params in param_sets:
                try:
                    # Update referer
                    self.session.headers['Referer'] = room_url

                    # Try POST
                    response = self.session.post(avail_url, data=params, timeout=15)

                    if response.status_code == 200:
                        try:
                            data = response.json()
                            if data and ('slots' in data or 'availability' in data or 'bookings' in data):
                                return data
                        except json.JSONDecodeError:
                            pass

                    # Try GET
                    response = self.session.get(avail_url, params=params, timeout=15)

                    if response.status_code == 200:
                        try:
                            data = response.json()
                            if data and ('slots' in data or 'availability' in data or 'bookings' in data):
                                return data
                        except json.JSONDecodeError:
                            pass

                except:
                    continue

        except Exception as e:
            logger.debug(f"Error fetching availability for room {room_id}: {e}")

        return None

    def is_available_at_time(self, avail_data: Dict, time_slot: str) -> Optional[bool]:
        """
        Check if room is available at specific time based on API data

        Args:
            avail_data: Data returned from get_room_availability()
            time_slot: Time in HH:MM format

        Returns:
            True if available, False if booked, None if can't determine
        """
        if not avail_data:
            return None

        slots = avail_data.get('slots', [])

        for slot in slots:
            start = slot.get('start', '')

            # Check if this slot matches our time
            if time_slot in start or start.startswith(time_slot):
                # Check status/class
                class_name = slot.get('className', slot.get('class', ''))
                status = slot.get('status', '')

                # Available indicators
                if 'avail' in str(class_name).lower() or status == 'available':
                    return True

                # Booked indicators
                if 'booked' in str(class_name).lower() or 'checkout' in str(class_name).lower():
                    return False

        return None

    def check_rooms(self, rooms: List[Dict], date: str, time_slot: str, max_check: int = 30) -> tuple:
        """Check multiple rooms for availability"""

        print(f"\n🔍 Checking REAL availability via UCL's API")
        print(f"   Target: {date} at {time_slot}")
        print(f"   Checking up to {max_check} rooms...\n")

        available = []
        booked = []
        uncertain = []

        for i, room in enumerate(rooms[:max_check]):
            room_id = room['id']
            name = room['name']

            print(f"   [{i+1}/{min(len(rooms), max_check)}] {name[:55]:<55} ", end="", flush=True)

            # Get availability data
            avail_data = self.get_room_availability(room_id, date)

            if avail_data:
                # Check if available at our time
                is_avail = self.is_available_at_time(avail_data, time_slot)

                if is_avail == True:
                    print("✅ AVAILABLE")
                    room_copy = room.copy()
                    room_copy['avail_data'] = avail_data
                    available.append(room_copy)
                elif is_avail == False:
                    print("❌ Booked")
                    booked.append(room)
                else:
                    print("⚠️  Uncertain")
                    uncertain.append(room)
            else:
                print("❌ API blocked")
                uncertain.append(room)

            # Small delay to avoid rate limiting
            time.sleep(0.3)

        print(f"\n   ✅ Available: {len(available)} | ❌ Booked: {len(booked)} | ⚠️  Uncertain: {len(uncertain)}")

        return available, booked, uncertain


def main():
    """Test the real availability checker"""
    import sys

    # Load rooms
    try:
        with open("ucl_rooms.json", 'r') as f:
            all_rooms = json.load(f)
    except FileNotFoundError:
        print("❌ Room data not found. Run: python3 ucl_scraper.py")
        return

    # Deduplicate
    unique_rooms = {}
    for room in all_rooms:
        if room['id'] not in unique_rooms:
            unique_rooms[room['id']] = room
    rooms = list(unique_rooms.values())

    # Parameters
    num_people = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    time_slot = sys.argv[2] if len(sys.argv) > 2 else "18:30"
    date = "2025-11-28"

    # Filter by capacity and sort
    suitable = [r for r in rooms if r['capacity'] >= num_people]
    suitable.sort(key=lambda r: r['capacity'])

    print(f"\n📊 Found {len(suitable)} rooms with capacity >= {num_people}")

    # Check availability
    checker = RealAvailabilityChecker()
    available, booked, uncertain = checker.check_rooms(suitable, date, time_slot, max_check=30)

    # Display results
    print("\n" + "=" * 90)
    print(f"\n🎯 ACTUALLY AVAILABLE FOR {num_people} PEOPLE AT {time_slot}:")
    print("=" * 90)

    if available:
        for i, room in enumerate(available, 1):
            print(f"\n{i}. {room['name']}")
            print(f"   👥 {room['capacity']} people | 📍 {room['location_name']}")
            print(f"   🏢 {room['zone_name']}")
            print(f"   ✅ CONFIRMED AVAILABLE via UCL API")
            print(f"   🔗 Book: {room['booking_url']}")
    else:
        print("\n😔 No rooms found available via automated checking")

    if uncertain:
        print(f"\n\n⚠️  {len(uncertain)} rooms need manual verification (API access limited):")
        for i, room in enumerate(uncertain[:10], 1):
            print(f"   {i}. {room['name']}")
            print(f"      {room['booking_url']}")

    print("\n" + "=" * 90)


if __name__ == "__main__":
    main()
