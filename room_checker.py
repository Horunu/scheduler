"""
Room Availability Checker
Handles logic for checking room availability based on capacity and time
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class RoomChecker:
    def __init__(self, rooms_file: str = "rooms.json", bookings_file: str = "bookings.json"):
        """Initialize the room checker with data files"""
        with open(rooms_file, 'r') as f:
            self.rooms = json.load(f)

        with open(bookings_file, 'r') as f:
            self.bookings = json.load(f)

    def filter_by_capacity(self, num_people: int) -> List[Dict]:
        """
        Filter rooms by capacity
        Returns rooms with capacity >= num_people
        """
        return [room for room in self.rooms if room['capacity'] >= num_people]

    def get_bookings_for_room(self, room_id: str, date: str) -> List[Dict]:
        """Get all bookings for a specific room on a specific date"""
        return [
            booking for booking in self.bookings
            if booking['room_id'] == room_id and booking['date'] == date
        ]

    def is_room_available(self, room_id: str, date: str, start_time: str, end_time: str) -> bool:
        """
        Check if a room is available for a specific time slot
        Returns True if room is free, False if booked
        """
        bookings = self.get_bookings_for_room(room_id, date)

        requested_start = datetime.strptime(start_time, "%H:%M")
        requested_end = datetime.strptime(end_time, "%H:%M")

        for booking in bookings:
            booking_start = datetime.strptime(booking['start_time'], "%H:%M")
            booking_end = datetime.strptime(booking['end_time'], "%H:%M")

            # Check for overlap
            if not (requested_end <= booking_start or requested_start >= booking_end):
                return False

        return True

    def get_next_booking(self, room_id: str, date: str, from_time: str) -> Optional[str]:
        """
        Get the next booking time for a room after a specific time
        Returns the start time of next booking, or None if no more bookings
        """
        bookings = self.get_bookings_for_room(room_id, date)
        current_time = datetime.strptime(from_time, "%H:%M")

        next_bookings = [
            datetime.strptime(booking['start_time'], "%H:%M")
            for booking in bookings
            if datetime.strptime(booking['start_time'], "%H:%M") > current_time
        ]

        if next_bookings:
            return min(next_bookings).strftime("%H:%M")
        return None

    def calculate_free_duration(self, room_id: str, date: str, start_time: str) -> float:
        """
        Calculate how long a room is free from start_time
        Returns duration in hours
        """
        # Default end of day
        end_of_day = datetime.strptime("18:00", "%H:%M")
        current_time = datetime.strptime(start_time, "%H:%M")

        next_booking_time = self.get_next_booking(room_id, date, start_time)

        if next_booking_time:
            next_booking = datetime.strptime(next_booking_time, "%H:%M")
            duration = (next_booking - current_time).total_seconds() / 3600
        else:
            duration = (end_of_day - current_time).total_seconds() / 3600

        return max(0, duration)

    def find_available_rooms(self, num_people: int, date: str, start_time: str,
                            duration_hours: float = 1.0) -> List[Dict]:
        """
        Find all available rooms for given capacity, date, and time
        Returns list of available rooms with their free duration
        """
        # Filter by capacity
        suitable_rooms = self.filter_by_capacity(num_people)

        # Calculate end time
        start_dt = datetime.strptime(start_time, "%H:%M")
        end_dt = start_dt + timedelta(hours=duration_hours)
        end_time = end_dt.strftime("%H:%M")

        available_rooms = []

        for room in suitable_rooms:
            if self.is_room_available(room['id'], date, start_time, end_time):
                free_duration = self.calculate_free_duration(room['id'], date, start_time)

                available_rooms.append({
                    'room': room,
                    'free_duration': free_duration
                })

        # Sort by capacity (smaller rooms first for efficiency)
        available_rooms.sort(key=lambda x: x['room']['capacity'])

        return available_rooms
