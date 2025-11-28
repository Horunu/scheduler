#!/usr/bin/env python3
"""
UCL Room Availability Tool - Live Integration
Finds available rooms from UCL's library booking system
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict
from pathlib import Path


def deduplicate_rooms(rooms: List[Dict]) -> List[Dict]:
    """Remove duplicate rooms (same ID) and keep best entry"""
    unique_rooms = {}

    for room in rooms:
        room_id = room['id']
        if room_id not in unique_rooms:
            unique_rooms[room_id] = room
        else:
            # Keep entry with more specific zone/group info (not '0')
            existing = unique_rooms[room_id]
            if room['zone_id'] != '0' and existing['zone_id'] == '0':
                unique_rooms[room_id] = room
            elif room['zone_id'] == existing['zone_id'] and \
                 room['group_id'] != '0' and existing['group_id'] == '0':
                unique_rooms[room_id] = room

    return list(unique_rooms.values())


def load_ucl_rooms(force_refresh: bool = False) -> List[Dict]:
    """
    Load UCL room data - from cache or by scraping

    Args:
        force_refresh: If True, re-scrape data from UCL

    Returns:
        List of room dictionaries (deduplicated)
    """
    cache_file = "ucl_rooms.json"

    # Check if cache exists and is recent (< 24 hours old)
    if not force_refresh and os.path.exists(cache_file):
        file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_file))
        if file_age < timedelta(hours=24):
            print(f"📦 Loading cached room data ({file_age.seconds // 3600}h old)...")
            with open(cache_file, 'r') as f:
                rooms = json.load(f)
                return deduplicate_rooms(rooms)

    # Scrape fresh data
    print("🔄 Fetching latest room data from UCL...")
    try:
        from ucl_scraper import UCLScraper
        scraper = UCLScraper()
        rooms = scraper.scrape_all_rooms(include_amenities=False)
        scraper.save_rooms_to_file(rooms, cache_file)
        return deduplicate_rooms(rooms)
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        # Fall back to cache if it exists
        if os.path.exists(cache_file):
            print("   Using cached data as fallback...")
            with open(cache_file, 'r') as f:
                rooms = json.load(f)
                return deduplicate_rooms(rooms)
        raise


def filter_rooms_by_capacity(rooms: List[Dict], num_people: int) -> List[Dict]:
    """Filter rooms that can accommodate the number of people"""
    return [room for room in rooms if room['capacity'] >= num_people]


def filter_by_location(rooms: List[Dict], location_filter: str = None) -> List[Dict]:
    """Optionally filter by location name"""
    if not location_filter:
        return rooms

    return [room for room in rooms
            if location_filter.lower() in room['location_name'].lower()]


def get_unique_locations(rooms: List[Dict]) -> List[str]:
    """Get list of unique location names"""
    locations = set(room['location_name'] for room in rooms)
    return sorted(locations)


def display_rooms(rooms: List[Dict], num_people: int, max_display: int = 20):
    """Display rooms in a formatted way"""
    if not rooms:
        print("\n❌ No rooms found matching your criteria.")
        print("💡 Try adjusting your requirements or check UCL's booking site directly:")
        print("   https://library-calendars.ucl.ac.uk/r/new")
        return

    print(f"\n✅ Found {len(rooms)} room(s) for {num_people} people")
    print("=" * 90)

    # Group by location for better organization
    rooms_by_location = {}
    for room in rooms:
        loc = room['location_name']
        if loc not in rooms_by_location:
            rooms_by_location[loc] = []
        rooms_by_location[loc].append(room)

    displayed = 0
    for location in sorted(rooms_by_location.keys()):
        location_rooms = rooms_by_location[location]

        print(f"\n📍 {location} ({len(location_rooms)} rooms)")
        print("-" * 90)

        for room in sorted(location_rooms, key=lambda x: x['capacity'])[:max_display - displayed]:
            print(f"\n  {room['name']}")
            print(f"     👥 Capacity: {room['capacity']} people")
            print(f"     📂 Category: {room['group_name']}")
            print(f"     🏢 Floor: {room['zone_name']}")
            print(f"     🔗 Check availability & book:")
            print(f"        {room['booking_url']}")

            displayed += 1
            if displayed >= max_display:
                break

        if displayed >= max_display:
            remaining = len(rooms) - displayed
            if remaining > 0:
                print(f"\n... and {remaining} more rooms")
                print(f"💡 Use filters or visit: https://library-calendars.ucl.ac.uk/r/new")
            break

    print("\n" + "=" * 90)
    print("ℹ️  Click the booking links above to see live availability and make reservations")


def main():
    """Main application entry point"""
    print("=" * 90)
    print("🏛️  UCL Room Finder - Live Integration")
    print("=" * 90)

    # Load room data
    try:
        rooms = load_ucl_rooms(force_refresh=False)
        print(f"📊 Loaded {len(rooms)} rooms from UCL library system")
    except Exception as e:
        print(f"\n❌ Failed to load room data: {e}")
        print("Please check your internet connection and try again.")
        return

    # Show available locations
    locations = get_unique_locations(rooms)
    print(f"\n📍 Available locations: {len(locations)}")
    for i, loc in enumerate(locations, 1):
        count = len([r for r in rooms if r['location_name'] == loc])
        print(f"   {i}. {loc} ({count} rooms)")

    # Get number of people
    while True:
        try:
            num_people_input = input("\n👥 How many people? ")
            num_people = int(num_people_input)
            if num_people > 0:
                break
            print("   Please enter a positive number")
        except ValueError:
            print("   Please enter a valid number")
        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 Exiting...")
            return

    # Optional: Filter by location
    print("\n📍 Filter by location? (press Enter to show all)")
    location_filter = input("   Location name (or partial match): ").strip()

    # Apply filters
    filtered_rooms = filter_rooms_by_capacity(rooms, num_people)

    if location_filter:
        filtered_rooms = filter_by_location(filtered_rooms, location_filter)
        if not filtered_rooms:
            print(f"\n⚠️  No rooms found matching '{location_filter}'. Showing all locations...")
            filtered_rooms = filter_rooms_by_capacity(rooms, num_people)

    # Display results
    display_rooms(filtered_rooms, num_people, max_display=20)

    # Help text
    print("\n💡 Tips:")
    print("   • Click the booking links to see real-time availability")
    print("   • You can filter by capacity, location, and booking times on UCL's site")
    print("   • Rooms are bookable by UCL students and staff")
    print("\n📝 To refresh room data: delete ucl_rooms.json and run again")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Exiting... Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
