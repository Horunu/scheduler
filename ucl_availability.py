"""
UCL Room Availability Checker
Queries live availability from UCL's LibCal system
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UCLAvailabilityChecker:
    """Checks real-time room availability from UCL LibCal system"""

    BASE_URL = "https://library-calendars.ucl.ac.uk"
    AVAILABILITY_ENDPOINT = f"{BASE_URL}/spaces/availability/grid"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest'
        })

    def check_availability(self, room_id: int, date: str, location_id: str = None,
                          group_id: str = None) -> Optional[List[Dict]]:
        """
        Check availability for a specific room on a specific date

        Args:
            room_id: The room/equipment ID (eid)
            date: Date in YYYY-MM-DD format
            location_id: Location ID (lid) - optional
            group_id: Group ID (gid) - optional

        Returns:
            List of time slot dictionaries with availability info
        """
        try:
            # First, visit the spaces page to get session cookies
            spaces_url = f"{self.BASE_URL}/spaces"
            if location_id:
                spaces_url += f"?lid={location_id}"

            try:
                self.session.get(spaces_url, timeout=15)
            except:
                pass  # Continue even if this fails

            # Prepare POST data
            data = {
                'eid': room_id,
                'start': date,
                'end': date,
                'pageIndex': 0,
                'pageSize': 100
            }

            if location_id:
                data['lid'] = location_id
            if group_id:
                data['gid'] = group_id

            # Add referer header
            self.session.headers.update({
                'Referer': spaces_url
            })

            # Make request
            response = self.session.post(
                self.AVAILABILITY_ENDPOINT,
                data=data,
                timeout=30
            )
            response.raise_for_status()

            # Parse JSON response
            result = response.json()
            slots = result.get('slots', [])

            logger.debug(f"Found {len(slots)} time slots for room {room_id}")
            return slots

        except requests.RequestException as e:
            logger.error(f"Failed to check availability for room {room_id}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse availability response: {e}")
            return None

    def is_available_at_time(self, slots: List[Dict], time_str: str,
                            duration_hours: float = 1.0) -> bool:
        """
        Check if room is available at a specific time

        Args:
            slots: List of time slots from check_availability()
            time_str: Time in HH:MM format (e.g., "14:00")
            duration_hours: How long you need the room (default 1 hour)

        Returns:
            True if available for the entire duration
        """
        if not slots:
            return False

        # Parse requested time
        try:
            target_time = datetime.strptime(time_str, "%H:%M").time()
            duration_delta = timedelta(hours=duration_hours)
        except ValueError:
            logger.error(f"Invalid time format: {time_str}")
            return False

        # Check each slot
        for slot in slots:
            # Parse slot time
            slot_start = slot.get('start', '')
            slot_end = slot.get('end', '')

            if not slot_start:
                continue

            try:
                # LibCal typically returns ISO format timestamps
                slot_start_dt = datetime.fromisoformat(slot_start.replace('Z', '+00:00'))
                slot_start_time = slot_start_dt.time()

                # Check if this slot matches our target time
                if slot_start_time.hour == target_time.hour and \
                   slot_start_time.minute == target_time.minute:

                    # Check if slot is available
                    class_name = slot.get('className', '')
                    if 's-lc-eq-avail' in class_name:
                        return True
                    else:
                        return False

            except (ValueError, AttributeError) as e:
                logger.debug(f"Could not parse slot time: {e}")
                continue

        return False

    def get_available_time_slots(self, slots: List[Dict]) -> List[Tuple[str, str]]:
        """
        Extract all available time slots

        Args:
            slots: List of time slots from check_availability()

        Returns:
            List of (start_time, end_time) tuples in HH:MM format
        """
        available_slots = []

        for slot in slots:
            class_name = slot.get('className', '')

            # Check if slot is available
            if 's-lc-eq-avail' in class_name:
                try:
                    start = slot.get('start', '')
                    end = slot.get('end', '')

                    if start and end:
                        # Parse ISO format
                        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))

                        start_time = start_dt.strftime("%H:%M")
                        end_time = end_dt.strftime("%H:%M")

                        available_slots.append((start_time, end_time))

                except (ValueError, AttributeError) as e:
                    logger.debug(f"Could not parse slot: {e}")
                    continue

        return available_slots

    def calculate_free_duration_from_time(self, slots: List[Dict],
                                         start_time: str) -> float:
        """
        Calculate how long a room is free starting from a specific time

        Args:
            slots: List of time slots from check_availability()
            start_time: Start time in HH:MM format

        Returns:
            Duration in hours that room is continuously free
        """
        available_slots = self.get_available_time_slots(slots)

        if not available_slots:
            return 0.0

        # Parse start time
        try:
            target = datetime.strptime(start_time, "%H:%M")
        except ValueError:
            return 0.0

        # Sort slots by start time
        sorted_slots = sorted(available_slots, key=lambda x: x[0])

        # Find continuous availability starting from target time
        duration = 0.0
        current_time = start_time

        for slot_start, slot_end in sorted_slots:
            # Check if slot is at or after our current time
            slot_start_dt = datetime.strptime(slot_start, "%H:%M")

            if slot_start <= current_time:
                # This slot covers our current time
                slot_end_dt = datetime.strptime(slot_end, "%H:%M")
                duration = (slot_end_dt - target).total_seconds() / 3600
                current_time = slot_end
            elif slot_start == current_time:
                # Continuous slot
                slot_end_dt = datetime.strptime(slot_end, "%H:%M")
                duration = (slot_end_dt - target).total_seconds() / 3600
                current_time = slot_end
            else:
                # Gap found - stop counting
                break

        return max(0.0, duration)

    def filter_available_rooms(self, rooms: List[Dict], date: str, time: str,
                              duration_hours: float = 1.0) -> List[Dict]:
        """
        Filter list of rooms to only those available at specified time

        Args:
            rooms: List of room dictionaries with 'id', 'location_id', 'group_id'
            date: Date in YYYY-MM-DD format
            time: Time in HH:MM format
            duration_hours: Required duration

        Returns:
            List of available rooms with added 'free_duration' field
        """
        available_rooms = []

        logger.info(f"Checking availability for {len(rooms)} rooms...")

        for i, room in enumerate(rooms):
            if i > 0 and i % 10 == 0:
                logger.info(f"Progress: {i}/{len(rooms)} rooms checked")

            room_id = room['id']
            location_id = room.get('location_id')
            group_id = room.get('group_id')

            # Check availability
            slots = self.check_availability(room_id, date, location_id, group_id)

            if slots and self.is_available_at_time(slots, time, duration_hours):
                # Calculate free duration
                free_duration = self.calculate_free_duration_from_time(slots, time)

                room_copy = room.copy()
                room_copy['free_duration'] = free_duration
                room_copy['available_slots'] = self.get_available_time_slots(slots)

                available_rooms.append(room_copy)

        logger.info(f"Found {len(available_rooms)} available rooms")
        return available_rooms


def main():
    """Test availability checker"""
    checker = UCLAvailabilityChecker()

    # Test with a known room (Student Centre study space)
    room_id = 18361  # Quiet Study Room 2.07
    date = "2025-11-28"
    time = "14:00"

    print(f"Checking availability for room {room_id} on {date} at {time}...")

    slots = checker.check_availability(room_id, date, location_id="872")

    if slots:
        print(f"Found {len(slots)} time slots")

        available_slots = checker.get_available_time_slots(slots)
        print(f"\nAvailable time slots:")
        for start, end in available_slots[:10]:  # Show first 10
            print(f"  {start} - {end}")

        if checker.is_available_at_time(slots, time):
            duration = checker.calculate_free_duration_from_time(slots, time)
            print(f"\n✅ Room is available at {time}")
            print(f"   Free for: {duration:.1f} hours")
        else:
            print(f"\n❌ Room is NOT available at {time}")
    else:
        print("Could not fetch availability data")


if __name__ == "__main__":
    main()
