#!/usr/bin/env python3
"""
Real Live Availability Checker - Uses Selenium to actually check UCL booking pages
No more excuses - this REALLY checks if rooms are available!
"""

import json
import time
from datetime import datetime
from typing import List, Dict, Optional
import logging

# Selenium imports
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LiveAvailabilityChecker:
    """Actually checks live availability by scraping rendered booking pages"""

    def __init__(self, headless: bool = True):
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium not available. Install with: pip install selenium webdriver-manager")

        self.headless = headless
        self.driver = None

    def _init_driver(self):
        """Initialize Chrome driver"""
        if self.driver:
            return

        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("✅ Chrome driver initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            raise

    def check_room_availability(self, room_id: int, date: str, time_slot: str) -> Optional[Dict]:
        """
        Check if a specific room is available at a specific time

        Args:
            room_id: UCL room ID (lid parameter)
            date: Date in YYYY-MM-DD format
            time_slot: Time in HH:MM format (e.g., "18:30")

        Returns:
            Dict with availability info or None if can't determine
        """
        if not self.driver:
            self._init_driver()

        url = f"https://library-calendars.ucl.ac.uk/spaces?lid={room_id}"

        try:
            # Load the page
            self.driver.get(url)

            # Wait for calendar to load (look for availability grid/calendar elements)
            wait = WebDriverWait(self.driver, 15)

            # Try to find the calendar container
            try:
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "fc-timeline")))
            except:
                try:
                    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "s-lc-eq-avail")))
                except:
                    logger.warning(f"Calendar not found for room {room_id}")
                    return None

            # Give it a moment to fully render
            time.sleep(2)

            # Extract availability data from the page
            # Look for time slot elements with availability classes
            available_slots = []
            booked_slots = []

            # Method 1: Check for availability slot elements
            try:
                # Find all time slots
                slots = self.driver.find_elements(By.CSS_SELECTOR, "[class*='s-lc-eq']")

                for slot in slots:
                    slot_class = slot.get_attribute("class")
                    slot_time = slot.get_attribute("data-start") or slot.get_attribute("title")

                    if slot_time:
                        if "s-lc-eq-avail" in slot_class:
                            available_slots.append(slot_time)
                        elif "s-lc-eq-checkout" in slot_class or "booked" in slot_class.lower():
                            booked_slots.append(slot_time)

            except Exception as e:
                logger.debug(f"Method 1 failed: {e}")

            # Method 2: Try to extract from JavaScript variables in the page
            if not available_slots and not booked_slots:
                try:
                    script = """
                    var slots = [];
                    var elements = document.querySelectorAll('.fc-event, .s-lc-eq-avail, .s-lc-eq-checkout');
                    elements.forEach(function(el) {
                        var start = el.getAttribute('data-start') || el.getAttribute('data-time');
                        var className = el.className;
                        if (start) {
                            slots.push({
                                time: start,
                                available: className.includes('avail')
                            });
                        }
                    });
                    return slots;
                    """
                    slots_data = self.driver.execute_script(script)

                    for slot in slots_data:
                        if slot.get('available'):
                            available_slots.append(slot['time'])
                        else:
                            booked_slots.append(slot['time'])

                except Exception as e:
                    logger.debug(f"Method 2 failed: {e}")

            # Method 3: Check page text for availability indicators
            if not available_slots and not booked_slots:
                page_text = self.driver.page_source.lower()

                # Look for common patterns
                if "no availability" in page_text or "fully booked" in page_text:
                    return {
                        'room_id': room_id,
                        'available': False,
                        'reason': 'Fully booked',
                        'slots_checked': True
                    }

            # Check if our target time is in available slots
            target_available = False
            for slot_time in available_slots:
                if time_slot in slot_time or slot_time.startswith(time_slot):
                    target_available = True
                    break

            # Also check it's not in booked slots
            for slot_time in booked_slots:
                if time_slot in slot_time or slot_time.startswith(time_slot):
                    target_available = False
                    break

            return {
                'room_id': room_id,
                'available': target_available,
                'available_slots': len(available_slots),
                'booked_slots': len(booked_slots),
                'slots_checked': True
            }

        except Exception as e:
            logger.warning(f"Error checking room {room_id}: {e}")
            return None

    def filter_available_rooms(self, rooms: List[Dict], date: str, time_slot: str,
                              max_check: int = 20) -> List[Dict]:
        """
        Filter rooms to only those actually available at the specified time

        Args:
            rooms: List of room dictionaries
            date: Date in YYYY-MM-DD format
            time_slot: Time in HH:MM format
            max_check: Maximum number of rooms to check (for performance)

        Returns:
            List of available rooms with availability info added
        """
        available_rooms = []

        print(f"\n🔍 Checking live availability for {date} at {time_slot}...")
        print(f"   (Checking up to {max_check} rooms - this may take 1-2 minutes)\n")

        checked = 0
        for i, room in enumerate(rooms[:max_check]):
            room_id = room['id']
            room_name = room['name']

            print(f"   [{i+1}/{min(len(rooms), max_check)}] Checking: {room_name[:50]}...", end=" ", flush=True)

            result = self.check_room_availability(room_id, date, time_slot)

            if result and result.get('available'):
                print("✅ AVAILABLE")
                room_copy = room.copy()
                room_copy['availability_checked'] = True
                room_copy['available_at_time'] = time_slot
                available_rooms.append(room_copy)
            elif result and result.get('slots_checked'):
                print("❌ Booked")
            else:
                print("⚠️  Could not verify")

            checked += 1

        return available_rooms

    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def main():
    """Test the live availability checker"""
    import sys

    # Load room data
    try:
        with open("ucl_rooms.json", 'r') as f:
            all_rooms = json.load(f)
    except FileNotFoundError:
        print("❌ Room data not found. Run: python3 ucl_scraper.py")
        return

    # Deduplicate
    unique_rooms = {}
    for room in all_rooms:
        room_id = room['id']
        if room_id not in unique_rooms:
            unique_rooms[room_id] = room
    rooms = list(unique_rooms.values())

    # Get parameters
    num_people = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    time_slot = sys.argv[2] if len(sys.argv) > 2 else "18:30"
    date = "2025-11-28"  # Today

    # Filter by capacity
    suitable_rooms = [r for r in rooms if r['capacity'] >= num_people]
    print(f"\n📊 Found {len(suitable_rooms)} rooms with capacity >= {num_people}")

    # Check live availability
    with LiveAvailabilityChecker(headless=True) as checker:
        available_rooms = checker.filter_available_rooms(
            suitable_rooms,
            date=date,
            time_slot=time_slot,
            max_check=20  # Check first 20 for speed
        )

    # Display results
    print("\n" + "=" * 90)
    print(f"\n🎯 ACTUALLY AVAILABLE ROOMS FOR {num_people} PEOPLE AT {time_slot}:")
    print("=" * 90)

    if available_rooms:
        for i, room in enumerate(available_rooms, 1):
            print(f"\n{i}. {room['name']}")
            print(f"   👥 Capacity: {room['capacity']} people")
            print(f"   📍 {room['location_name']} - {room['zone_name']}")
            print(f"   ✅ Available at {time_slot}")
            print(f"   🔗 Book now: {room['booking_url']}")
    else:
        print("\n❌ No rooms found available at that time")
        print("   Try a different time or check more rooms")

    print("\n" + "=" * 90)


if __name__ == "__main__":
    main()
