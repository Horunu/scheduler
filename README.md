# UCL Room Availability Checker

A simple CLI tool to find available rooms at UCL based on capacity and time requirements.

## Features

- **Capacity-based filtering**: Only suggests rooms that can accommodate your group size
- **Time-based availability**: Check room availability for now or specific times
- **Duration calculation**: Shows how long each room is available
- **Room details**: Displays building, floor, capacity, and facilities

## Current Status

This is a **prototype** using synthetic data. Future versions will connect to UCL's live booking system.

## Installation

No external dependencies required! Just Python 3.6+

```bash
# Make the script executable
chmod +x main.py
```

## Usage

Run the tool:

```bash
python3 main.py
```

Or if executable:

```bash
./main.py
```

### Example Workflow

1. **Enter number of people**: e.g., `5`
2. **Choose timing**:
   - "Now?" - Select `y` for immediate availability
   - If not now, specify:
     - "Today?" - `y` or `n`
     - "What time?" - Enter time in 24h format (e.g., `14:30`)
3. **View results**: Available rooms with duration and details

### Example Output

```
================================================================================
🏛️  UCL Room Availability Checker
================================================================================

👥 How many people? 5

⏰ Do you want the room now? (Y/n): y

🔍 Searching for rooms available now (from 13:00)...

✅ Found 4 available room(s) for 5 people:

================================================================================

1. Room 202 - Wilkins Building
   📍 Building: Wilkins Building, Floor 2
   👥 Capacity: 6 people
   ⏱️  Available for: 5 hours
   🔧 Facilities: Whiteboard

2. Room 102 - Darwin Building
   📍 Building: Darwin Building, Floor 1
   👥 Capacity: 8 people
   ⏱️  Available for: 5 hours
   🔧 Facilities: Whiteboard, Projector, Video Conference

...
```

## Data Files

### rooms.json
Contains room information:
- Room ID
- Name and location
- Capacity
- Facilities

### bookings.json
Contains booking data:
- Room ID
- Date and time slots
- Booked by information

## Project Structure

```
scheduler/
├── main.py              # CLI interface
├── room_checker.py      # Core availability logic
├── rooms.json           # Room data
├── bookings.json        # Booking data
└── README.md           # This file
```

## Future Enhancements

- [ ] Connect to UCL live booking system
- [ ] Web scraping for real-time data
- [ ] Support for date ranges
- [ ] Filter by building/facilities
- [ ] Export results
- [ ] Booking integration

## Technical Notes

**Why Python?**
- Excellent web scraping libraries (BeautifulSoup, Selenium, Scrapy)
- Easy to handle unoptimized websites
- Simple CLI development
- Great data processing capabilities

**Future UCL Integration:**
When connecting to UCL's booking system, we'll likely use:
- `requests` for HTTP requests
- `beautifulsoup4` for HTML parsing
- `selenium` if JavaScript rendering is needed
- Caching to minimize requests
