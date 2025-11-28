"""
UCL Library Booking System Scraper
Extracts room data from the LibCal (Springshare) system
"""

import re
import json
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UCLScraper:
    """Scrapes UCL library booking system for room data"""

    BASE_URL = "https://library-calendars.ucl.ac.uk"
    BOOKING_URL = f"{BASE_URL}/r/new"

    # Feature/amenity mappings based on UCL's system
    AMENITIES_MAP = {
        "Enclosed Study Room/Pod": "enclosed",
        "Height Adjustable Desk": "adjustable_desk",
        "Laptop Docking Station with Monitor": "docking_station",
        "Laptop/Device Charging Available": "charging",
        "Quiet Study Seat/Space": "quiet",
        "Social Study Seat/Space": "social",
        "Soundproof Space": "soundproof",
        "Wheelchair Accessible": "accessible"
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def fetch_page(self) -> str:
        """Fetch the main booking page"""
        try:
            response = self.session.get(self.BOOKING_URL, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch booking page: {e}")
            raise

    def extract_location_names(self, html: str) -> Dict[str, str]:
        """
        Extract location names from HTML dropdown/select elements
        Returns dict mapping location_id -> location_name
        """
        soup = BeautifulSoup(html, 'lxml')
        location_map = {}

        # Look for location dropdown (typically <select id="...location..." name="lid">)
        location_select = soup.find('select', {'id': re.compile(r'location', re.I)}) or \
                         soup.find('select', {'name': 'lid'})

        if location_select:
            options = location_select.find_all('option')
            for option in options:
                loc_id = option.get('value')
                loc_name = option.text.strip()
                if loc_id and loc_name and loc_id != '0':
                    location_map[str(loc_id)] = loc_name
            logger.info(f"Extracted {len(location_map)} location names from HTML dropdown")
        else:
            logger.warning("Could not find location dropdown in HTML")

        return location_map

    def extract_springy_page_data(self, html: str) -> Optional[Dict]:
        """
        Extract the springyPage JavaScript object from HTML
        This contains all the room/location/capacity mappings
        """
        # Look for the springyPage object in script tags
        # Try multiple patterns as the format might vary
        patterns = [
            r'var\s+springyPage\s*=\s*(\{[\s\S]*?\});',
            r'springyPage\s*=\s*(\{[\s\S]*?\});',
            r'window\.springyPage\s*=\s*(\{[\s\S]*?\});'
        ]

        json_str = None
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                json_str = match.group(1)
                break

        if not json_str:
            logger.error("Could not find springyPage object in HTML")
            # Save HTML for debugging
            with open('debug_ucl_page.html', 'w', encoding='utf-8') as f:
                f.write(html)
            logger.info("Saved HTML to debug_ucl_page.html for inspection")
            return None

        try:
            # Aggressive JavaScript to JSON conversion
            # 1. Remove comments
            json_str = re.sub(r'//.*?\n', '\n', json_str)
            json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)

            # 2. Add quotes around unquoted property names
            # Match: word characters followed by colon (property: value)
            json_str = re.sub(r'([,\{\s])(\w+):', r'\1"\2":', json_str)

            # 3. Remove trailing commas before } or ]
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)

            # 4. Handle single quotes in strings (convert to double quotes)
            # Be careful not to break escaped quotes
            json_str = re.sub(r"'([^']*)'", r'"\1"', json_str)

            data = json.loads(json_str)
            logger.info("Successfully parsed springyPage data")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse springyPage JSON: {e}")
            # Save for debugging
            with open('debug_springy_page_failed.json', 'w') as f:
                f.write(json_str[:10000])  # First 10k chars
            logger.info(f"Saved debug output. Error at: {e}")
            return None

    def parse_room_hierarchy(self, springy_data: Dict) -> List[Dict]:
        """
        Parse the complex nested structure from springyPage
        Returns a flat list of all rooms with their properties
        """
        rooms = []

        # Extract the nested mappings
        zones_by_location = springy_data.get('zoneIdNameModelsByLocationId', {})
        groups_by_location = springy_data.get('groupIdNameModelsByLocationId', {})
        capacity_by_loc_zone = springy_data.get('capacityIdNameModelsByLocationAndZone', {})
        items_by_all = springy_data.get('itemIdNameModelsByLocationCapacityZoneAndGroup', {})

        # Get location names (passed from scraper)
        location_map = springy_data.get('_location_names', {})
        if location_map:
            logger.info(f"Using {len(location_map)} location names")
        else:
            logger.warning("No location names provided, will use IDs")

        # Iterate through the hierarchy: Location → Zone → Group → Capacity → Items
        for loc_id, zones in zones_by_location.items():
            location_name = location_map.get(loc_id, f"Location {loc_id}")

            # Get groups for this location
            location_groups = groups_by_location.get(loc_id, [])

            # Get items for this location (drill down through nested structure)
            if loc_id in items_by_all:
                for capacity_id, capacity_data in items_by_all[loc_id].items():
                    if isinstance(capacity_data, dict):
                        for zone_id, zone_data in capacity_data.items():
                            if isinstance(zone_data, dict):
                                for group_id, items in zone_data.items():
                                    if isinstance(items, list):
                                        # Get zone name
                                        zone_name = next((z['name'] for z in zones if str(z['id']) == zone_id), f"Zone {zone_id}")

                                        # Get group name
                                        group_name = next((g['name'] for g in location_groups if str(g['id']) == group_id), f"Group {group_id}")

                                        # Parse capacity
                                        capacity = self._parse_capacity(capacity_id)

                                        # Add each room/item
                                        for item in items:
                                            room = {
                                                'id': item['id'],
                                                'name': item['name'],
                                                'location_id': loc_id,
                                                'location_name': location_name,
                                                'zone_id': zone_id,
                                                'zone_name': zone_name,
                                                'group_id': group_id,
                                                'group_name': group_name,
                                                'capacity': capacity,
                                                'capacity_id': capacity_id,
                                                'booking_url': f"{self.BASE_URL}/spaces?lid={item['id']}"
                                            }
                                            rooms.append(room)

        logger.info(f"Extracted {len(rooms)} rooms from UCL system")

        # Deduplicate by room ID (keep first occurrence with best info)
        unique_rooms = {}
        for room in rooms:
            room_id = room['id']
            if room_id not in unique_rooms:
                unique_rooms[room_id] = room
            else:
                # Keep the entry with more specific zone/group info
                existing = unique_rooms[room_id]
                if room['zone_id'] != '0' and existing['zone_id'] == '0':
                    unique_rooms[room_id] = room
                elif room['group_id'] != '0' and existing['group_id'] == '0':
                    unique_rooms[room_id] = room

        rooms_list = list(unique_rooms.values())
        logger.info(f"After deduplication: {len(rooms_list)} unique rooms")
        return rooms_list

    def _parse_capacity(self, capacity_id: str) -> int:
        """
        Parse capacity from capacity_id
        UCL uses: -1 (single), 0 (2 people), 1 (3), 2 (4-6), 3 (7+)
        """
        capacity_map = {
            '-1': 1,
            '0': 2,
            '1': 3,
            '2': 5,  # Average of 4-6
            '3': 8,  # 7+ assume 8
            '4': 10  # Large groups
        }
        return capacity_map.get(str(capacity_id), 1)

    def fetch_amenities_from_room_page(self, room_id: int) -> List[str]:
        """
        Fetch detailed amenities for a specific room
        This requires an additional request per room
        """
        try:
            url = f"{self.BASE_URL}/spaces?lid={room_id}"
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'lxml')
            amenities = []

            # Look for amenity checkboxes or lists
            # LibCal typically shows amenities in a specific section
            amenity_section = soup.find('div', class_='s-lc-eq-checkout')
            if amenity_section:
                checkboxes = amenity_section.find_all('input', type='checkbox')
                for checkbox in checkboxes:
                    label = checkbox.find_next('label')
                    if label:
                        amenities.append(label.text.strip())

            return amenities
        except Exception as e:
            logger.warning(f"Failed to fetch amenities for room {room_id}: {e}")
            return []

    def scrape_all_rooms(self, include_amenities: bool = False) -> List[Dict]:
        """
        Main scraping function: fetches all room data

        Args:
            include_amenities: If True, makes additional requests for detailed amenities
                             (slower but more complete)
        """
        logger.info("Starting UCL room scraping...")

        # Fetch main page
        html = self.fetch_page()

        # Extract location names from HTML
        location_names = self.extract_location_names(html)

        # Extract springyPage data
        springy_data = self.extract_springy_page_data(html)
        if not springy_data:
            raise Exception("Failed to extract room data from UCL website")

        # Add location names to springy data
        springy_data['_location_names'] = location_names

        # Parse room hierarchy
        rooms = self.parse_room_hierarchy(springy_data)

        # Optionally fetch detailed amenities (slow!)
        if include_amenities and rooms:
            logger.info(f"Fetching detailed amenities for {len(rooms)} rooms...")
            logger.warning("This may take several minutes...")

            for i, room in enumerate(rooms):
                if i > 0 and i % 10 == 0:
                    logger.info(f"Progress: {i}/{len(rooms)} rooms processed")

                amenities = self.fetch_amenities_from_room_page(room['id'])
                room['amenities'] = amenities

        return rooms

    def save_rooms_to_file(self, rooms: List[Dict], filename: str = "ucl_rooms.json"):
        """Save scraped room data to JSON file"""
        with open(filename, 'w') as f:
            json.dump(rooms, f, indent=2)
        logger.info(f"Saved {len(rooms)} rooms to {filename}")


def main():
    """Test the scraper"""
    scraper = UCLScraper()

    # Scrape all rooms (without detailed amenities for speed)
    rooms = scraper.scrape_all_rooms(include_amenities=False)

    # Show sample
    print(f"\n{'='*80}")
    print(f"Successfully scraped {len(rooms)} rooms from UCL")
    print(f"{'='*80}\n")

    if rooms:
        print("Sample rooms:")
        for room in rooms[:5]:
            print(f"\n  {room['name']}")
            print(f"    Location: {room['location_name']}")
            print(f"    Zone: {room['zone_name']}")
            print(f"    Category: {room['group_name']}")
            print(f"    Capacity: {room['capacity']} people")
            print(f"    URL: {room['booking_url']}")

    # Save to file
    scraper.save_rooms_to_file(rooms)

    return rooms


if __name__ == "__main__":
    main()
