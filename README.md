# UCL Room Availability Checker

A powerful CLI tool to find available study spaces and meeting rooms at UCL, integrated with the live UCL library booking system.

## Features

### ✅ Live UCL Integration
- **Real room data**: Scrapes 92+ study spaces from UCL's library booking system
- **11 library locations**: Student Centre, Science Library, Bartlett, IOE, and more
- **Smart caching**: Room data cached for 24 hours to reduce load times
- **Direct booking links**: Click-through to UCL's system for real-time availability

### 🎯 Smart Filtering
- **Capacity-based**: Only shows rooms that can accommodate your group size
- **Location filtering**: Search by library name (e.g., "student", "science", "bartlett")
- **Organized display**: Rooms grouped by location for easy browsing
- **Sorted results**: Smaller rooms shown first for efficient space usage

### 📊 Comprehensive Room Data
- Room names and IDs
- Exact capacities (1-20+ people)
- Floor and zone information
- Room categories (study pods, group rooms, etc.)
- Building locations

## Installation

### Requirements
- Python 3.6+
- Internet connection (for scraping UCL data)

### Setup

```bash
# Install dependencies
pip install requests beautifulsoup4 lxml

# Make scripts executable
chmod +x main_ucl.py
chmod +x ucl_scraper.py
```

## Usage

### Quick Start

```bash
# Run the main tool
python3 main_ucl.py

# Or if executable
./main_ucl.py
```

### Example Session

```
🏛️  UCL Room Finder - Live Integration
==========================================

📦 Loading cached room data...
📊 Loaded 92 rooms from UCL library system

📍 Available locations: 11
   1. Bartlett Library (1 rooms)
   2. Cruciform Hub (6 rooms)
   3. Science Library (15 rooms)
   4. Student Centre (39 rooms)
   ...

👥 How many people? 5

📍 Filter by location? (press Enter to show all)
   Location name (or partial match): student

✅ Found 12 room(s) for 5 people

📍 Student Centre (12 rooms)
─────────────────────────────────────────

  Group Study Room 2.02
     👥 Capacity: 5 people
     📂 Category: Group Study
     🏢 Floor: Second Floor
     🔗 Check availability & book:
        https://library-calendars.ucl.ac.uk/spaces?lid=18444

  ...
```

### Workflow

1. **Enter number of people**: Tool filters rooms by capacity
2. **Optional location filter**: Narrow down by library/building name
3. **Browse results**: View rooms organized by location
4. **Check availability**: Click booking links to see real-time availability on UCL's site
5. **Make booking**: Reserve directly through UCL's system

## How It Works

### Room Data Scraping

The tool extracts room data from UCL's LibCal (Springshare) booking system:

1. **Fetches** the main booking page (`https://library-calendars.ucl.ac.uk/r/new`)
2. **Extracts** the `springyPage` JavaScript object containing all room mappings
3. **Parses** the hierarchical data structure:
   - Location → Zone (floor) → Group (category) → Capacity → Individual rooms
4. **Deduplicates** entries to ensure each room appears once
5. **Caches** data locally for 24 hours

### Data Structure

Each room includes:
```python
{
  "id": 18444,
  "name": "Group Study Room 2.02",
  "location_id": "872",
  "location_name": "Student Centre",
  "zone_id": "427",
  "zone_name": "Second Floor",
  "group_id": "5428",
  "group_name": "Group Study",
  "capacity": 5,
  "booking_url": "https://library-calendars.ucl.ac.uk/spaces?lid=18444"
}
```

### Filtering Logic

- **Capacity**: Shows rooms with `capacity >= requested_people`
- **Location**: Case-insensitive partial matching (e.g., "sci" matches "Science Library")
- **Sorting**: Smallest suitable rooms first (efficient space usage)

## Project Structure

```
scheduler/
├── main_ucl.py              # Main CLI application (USE THIS!)
├── ucl_scraper.py           # UCL data scraper
├── ucl_availability.py      # Availability checker (experimental)
├── ucl_rooms.json           # Cached room data (auto-generated)
│
├── main.py                  # Old prototype with synthetic data
├── room_checker.py          # Old prototype logic
├── rooms.json               # Old synthetic room data
├── bookings.json            # Old synthetic booking data
│
├── README.md                # This file
├── requirements.txt         # Python dependencies
└── .gitignore              # Git ignore rules
```

## Available Locations

The tool covers **11 UCL library locations**:

1. **Student Centre** (39 rooms) - Main campus hub
2. **Science Library** (15 rooms) - DMS Watson Building
3. **Institute of Education Library** (9 rooms)
4. **Cruciform Hub** (6 rooms) - Medical Sciences
5. **Graduate Hub** (4 rooms) - Postgraduate spaces only
6. **Royal Free Hospital Medical Library** (5 rooms)
7. **Institute of Archaeology Library** (4 rooms)
8. **UCL East Library (Marshgate)** (5 rooms)
9. **SSEES Library** (2 rooms)
10. **The Joint Library of Ophthalmology** (2 rooms)
11. **Bartlett Library** (1 room)

## Advanced Usage

### Refresh Room Data

```bash
# Delete cache to force refresh
rm ucl_rooms.json

# Run tool (will re-scrape from UCL)
python3 main_ucl.py
```

### Standalone Scraper

```bash
# Scrape room data only
python3 ucl_scraper.py

# Output: ucl_rooms.json with all rooms
```

### Integration Notes

The tool provides **direct booking links** rather than attempting to scrape availability because:
- UCL's LibCal availability API is protected/requires authentication
- Direct links ensure users see real-time, accurate availability
- Booking must go through UCL's official system anyway
- This approach is more robust to UCL site changes

## Tips

- **Best results**: Use specific capacity numbers (e.g., 5 people, not "about 5")
- **Location filters**: Try partial names ("bart" for Bartlett, "sci" for Science)
- **Peak times**: Check availability on UCL's site for popular times
- **Postgraduate**: Graduate Hub spaces require UCL postgraduate status
- **Accessibility**: Check room details on booking pages for accessibility info

## Future Enhancements

- [ ] Scrape detailed amenities for each room
- [ ] Add time-of-day availability heuristics
- [ ] Filter by room features (soundproof, monitors, etc.)
- [ ] Export results to CSV/JSON
- [ ] Web interface
- [ ] Mobile app

## Troubleshooting

### "Failed to load room data"
- Check internet connection
- UCL's booking system might be down
- Try deleting `ucl_rooms.json` to force refresh

### "No rooms found"
- Try lower capacity number
- Remove location filter
- Check UCL's booking site directly

### Slow first run
- First run scrapes all data from UCL (~30 seconds)
- Subsequent runs use cache (instant)
- Cache refreshes automatically after 24 hours

## Technical Details

### Dependencies
- `requests`: HTTP client for web scraping
- `beautifulsoup4`: HTML parsing
- `lxml`: Fast XML/HTML parser

### UCL Booking System
- **Platform**: LibCal by Springshare
- **Data source**: JavaScript object embedded in page
- **Format**: Nested JSON structure (locations → zones → groups → capacities → items)
- **Rate limiting**: Tool uses caching to minimize requests

### Design Decisions

**Why not scrape live availability?**
- UCL's availability API requires session cookies and specific headers
- API endpoints may be protected or rate-limited
- Booking must be done through UCL's authenticated system anyway
- Direct links provide more reliable, up-to-date information

**Why cache data?**
- Room metadata changes infrequently
- Reduces load on UCL's servers
- Faster user experience
- 24-hour cache balances freshness with performance

## Development

### Running Tests

```bash
# Test scraper
python3 ucl_scraper.py

# Test availability checker (experimental)
python3 ucl_availability.py

# Test main tool
python3 main_ucl.py
```

### Code Style
- Functions have docstrings
- Type hints for major functions
- Logging for debugging
- Error handling with fallbacks

## License

Educational/research project. Respects UCL's booking system and usage policies.

## Acknowledgments

- UCL Library Services for providing the booking system
- LibCal (Springshare) platform
- UCL students and staff who will use this tool

---

**Made with ❤️ for the UCL community**

For issues or suggestions, check the repository issues page.
