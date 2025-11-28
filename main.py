#!/usr/bin/env python3
"""
UCL Room Availability Tool
Simple CLI tool to find available rooms based on capacity and time
"""

from datetime import datetime, timedelta
from room_checker import RoomChecker


def get_yes_no_input(prompt: str, default: bool = True) -> bool:
    """Get yes/no input from user"""
    default_str = "Y/n" if default else "y/N"
    while True:
        response = input(f"{prompt} ({default_str}): ").strip().lower()

        if not response:
            return default

        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' or 'n'")


def get_number_input(prompt: str) -> int:
    """Get a positive number from user"""
    while True:
        try:
            num = int(input(prompt))
            if num > 0:
                return num
            else:
                print("Please enter a positive number")
        except ValueError:
            print("Please enter a valid number")


def get_time_input(prompt: str) -> str:
    """Get time input in HH:MM format"""
    while True:
        time_str = input(prompt)
        try:
            # Validate format
            datetime.strptime(time_str, "%H:%M")
            return time_str
        except ValueError:
            print("Please enter time in HH:MM format (e.g., 14:30)")


def format_duration(hours: float) -> str:
    """Format duration in a readable way"""
    if hours >= 1:
        whole_hours = int(hours)
        minutes = int((hours - whole_hours) * 60)
        if minutes > 0:
            return f"{whole_hours} hour{'s' if whole_hours != 1 else ''} and {minutes} minutes"
        else:
            return f"{whole_hours} hour{'s' if whole_hours != 1 else ''}"
    else:
        minutes = int(hours * 60)
        return f"{minutes} minutes"


def display_available_rooms(available_rooms, num_people):
    """Display available rooms in a formatted way"""
    if not available_rooms:
        print("\n❌ No rooms available matching your criteria.")
        return

    print(f"\n✅ Found {len(available_rooms)} available room(s) for {num_people} people:\n")
    print("=" * 80)

    for idx, room_info in enumerate(available_rooms, 1):
        room = room_info['room']
        duration = room_info['free_duration']

        print(f"\n{idx}. {room['name']}")
        print(f"   📍 Building: {room['building']}, Floor {room['floor']}")
        print(f"   👥 Capacity: {room['capacity']} people")
        print(f"   ⏱️  Available for: {format_duration(duration)}")
        print(f"   🔧 Facilities: {', '.join(room['facilities'])}")

    print("\n" + "=" * 80)


def main():
    """Main application entry point"""
    print("=" * 80)
    print("🏛️  UCL Room Availability Checker")
    print("=" * 80)

    # Initialize room checker
    checker = RoomChecker()

    # Get number of people
    num_people = get_number_input("\n👥 How many people? ")

    # Get time preference
    want_now = get_yes_no_input("\n⏰ Do you want the room now?", default=True)

    if want_now:
        # Use current time (for demo, we'll use a fixed time in business hours)
        current_time = "13:00"  # Simulated current time
        date = "2025-11-28"  # Today (from env)
        print(f"\n🔍 Searching for rooms available now (from {current_time})...")

    else:
        # Ask if today
        want_today = get_yes_no_input("📅 Do you want the room today?", default=True)

        if want_today:
            date = "2025-11-28"  # Today (from env)
        else:
            # For prototype, we'll just use tomorrow
            date = "2025-11-29"
            print(f"   Using date: {date}")

        # Get specific time
        current_time = get_time_input("🕐 What time? (HH:MM format, e.g., 14:30): ")
        print(f"\n🔍 Searching for rooms available at {current_time} on {date}...")

    # Find available rooms
    available_rooms = checker.find_available_rooms(
        num_people=num_people,
        date=date,
        start_time=current_time,
        duration_hours=1.0  # Looking for at least 1 hour availability
    )

    # Display results
    display_available_rooms(available_rooms, num_people)

    print("\n💡 Tip: For future versions, this will connect to UCL's live booking system!")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Exiting... Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
