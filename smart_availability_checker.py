#!/usr/bin/env python3
"""
Smart Availability Checker - No Selenium needed!
Parses the page HTML and embedded JavaScript to extract availability
"""

import requests
import re
import json
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SmartAvailabilityChecker:
    """Checks availability by parsing HTML and embedded data"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def check_room_availability(self, room_id: int, date: str, time_slot: str) -> Optional[Dict]:
        """
        Check room availability by parsing the booking page

        Returns:
            Dict with availability status or None
        """
        url = f"https://library-calendars.ucl.ac.uk/spaces?lid={room_id}"

        try:
            response = self.session.get(url, timeout=20)
            response.raise_for_status()

            html = response.text
            soup = BeautifulSoup(html, 'lxml')

            # Method 1: Look for embedded availability data in JavaScript
            availability_data = self._extract_js_availability(html, date, time_slot)
            if availability_data:
                return availability_data

            # Method 2: Parse calendar HTML elements
            availability_data = self._parse_calendar_html(soup, date, time_slot)
            if availability_data:
                return availability_data

            # Method 3: Check for "fully booked" or "no availability" messages
            page_text = soup.get_text().lower()
            if "no availability" in page_text or "fully booked" in page_text:
                return {
                    'room_id': room_id,
                    'available': False,
                    'reason': 'Page indicates fully booked'
                }

            # If we can't determine, return uncertain
            return {
                'room_id': room_id,
                'available': None,
                'reason': 'Could not parse availability data'
            }

        except Exception as e:
            logger.debug(f"Error checking room {room_id}: {e}")
            return None

    def _extract_js_availability(self, html: str, date: str, time_slot: str) -> Optional[Dict]:
        """Extract availability from embedded JavaScript data"""

        # Look for calendar data or availability arrays in JavaScript
        patterns = [
            r'availability\s*[:=]\s*(\{[^}]+\}|\[[^\]]+\])',
            r'slots\s*[:=]\s*(\[[^\]]+\])',
            r'bookings\s*[:=]\s*(\[[^\]]+\])',
            r'calendar\s*[:=]\s*(\{[\s\S]{0,5000}?\})',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html)
            for match in matches:
                try:
                    # Clean and parse JSON
                    json_str = match
                    # Basic JavaScript to JSON conversion
                    json_str = re.sub(r'([,\{\s])(\w+):', r'\1"\2":', json_str)
                    json_str = re.sub(r"'([^']*)'", r'"\1"', json_str)

                    data = json.loads(json_str)

                    # Check if this data contains our time slot
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                item_time = item.get('time', item.get('start', ''))
                                if time_slot in str(item_time):
                                    is_available = item.get('available', item.get('status') == 'available')
                                    return {
                                        'room_id': 'unknown',
                                        'available': bool(is_available),
                                        'source': 'javascript_data'
                                    }
                except:
                    continue

        return None

    def _parse_calendar_html(self, soup: BeautifulSoup, date: str, time_slot: str) -> Optional[Dict]:
        """Parse calendar HTML elements for availability"""

        # Look for calendar grid cells or time slot elements
        calendar_elements = soup.find_all(class_=re.compile(r'(fc-|calendar|slot|time)'))

        available_count = 0
        booked_count = 0

        for elem in calendar_elements:
            classes = elem.get('class', [])
            class_str = ' '.join(classes) if isinstance(classes, list) else str(classes)

            # Check if this is an availability indicator
            if 'avail' in class_str.lower():
                available_count += 1
            elif 'booked' in class_str.lower() or 'unavail' in class_str.lower():
                booked_count += 1

        # If we found availability indicators, make an educated guess
        if available_count > 0 or booked_count > 0:
            # If more available than booked, likely available
            return {
                'room_id': 'unknown',
                'available': available_count > booked_count,
                'confidence': 'low',
                'source': 'html_parsing'
            }

        return None

    def filter_available_rooms(self, rooms: List[Dict], date: str, time_slot: str,
                              max_check: int = 30, parallel: bool = False) -> List[Dict]:
        """
        Filter rooms by actual availability

        Args:
            rooms: List of room dicts
            date: Date in YYYY-MM-DD
            time_slot: Time in HH:MM
            max_check: Max rooms to check
            parallel: Whether to use parallel requests (faster but heavier)

        Returns:
            List of available rooms
        """
        print(f"\n🔍 Checking availability for {date} at {time_slot}")
        print(f"   Analyzing up to {max_check} rooms...\n")

        available_rooms = []
        uncertain_rooms = []

        for i, room in enumerate(rooms[:max_check]):
            room_id = room['id']
            room_name = room['name']

            print(f"   [{i+1}/{min(len(rooms), max_check)}] {room_name[:55]:<55} ", end="", flush=True)

            result = self.check_room_availability(room_id, date, time_slot)

            if result:
                if result.get('available') == True:
                    print("✅ LIKELY AVAILABLE")
                    room_copy = room.copy()
                    room_copy['availability_status'] = result
                    available_rooms.append(room_copy)
                elif result.get('available') == False:
                    print("❌ Likely booked")
                else:
                    print("⚠️  Uncertain - check manually")
                    room_copy = room.copy()
                    uncertain_rooms.append(room_copy)
            else:
                print("⚠️  Could not check")

        print(f"\n   Found: {len(available_rooms)} likely available, {len(uncertain_rooms)} uncertain")

        return available_rooms, uncertain_rooms


def main():
    """Test the smart checker"""
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

    # Filter by capacity
    suitable_rooms = [r for r in rooms if r['capacity'] >= num_people]
    suitable_rooms.sort(key=lambda r: r['capacity'])  # Smallest first

    print(f"\n📊 Found {len(suitable_rooms)} rooms with capacity >= {num_people}")

    # Check availability
    checker = SmartAvailabilityChecker()
    available_rooms, uncertain_rooms = checker.filter_available_rooms(
        suitable_rooms,
        date=date,
        time_slot=time_slot,
        max_check=30
    )

    # Display results
    print("\n" + "=" * 90)
    print(f"\n🎯 ROOMS LIKELY AVAILABLE FOR {num_people} PEOPLE AT {time_slot}:")
    print("=" * 90)

    if available_rooms:
        for i, room in enumerate(available_rooms, 1):
            print(f"\n{i}. {room['name']}")
            print(f"   👥 {room['capacity']} people | 📍 {room['location_name']}")
            print(f"   🏢 {room['zone_name']} | 📂 {room['group_name']}")
            print(f"   🔗 {room['booking_url']}")
    else:
        print("\n⚠️  Could not confirm availability through automated checking")

    if uncertain_rooms:
        print(f"\n💡 {len(uncertain_rooms)} rooms need manual verification:")
        for i, room in enumerate(uncertain_rooms[:5], 1):
            print(f"   {i}. {room['name']} - {room['booking_url']}")

    print("\n" + "=" * 90)
    print("📝 Note: Automated checking has limitations. Always verify on UCL's booking page!")
    print()


if __name__ == "__main__":
    main()
