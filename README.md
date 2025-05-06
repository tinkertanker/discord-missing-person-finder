# Discord Attendance Checker

A Discord bot for checking attendance in a hackathon by comparing Discord members against an attendee list.

## Setup

1. Clone the repository
2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in your Discord token and other configuration

## Testing the Connection

To verify your Discord bot token and environment are set up correctly:

1. Edit the `.env` file and add your Discord bot token and Guild ID:
   ```
   DISCORD_TOKEN=your_actual_token_here
   GUILD_ID=your_server_id_here
   ```

2. Make sure your bot is added to your server with proper permissions:
   - The bot needs "Server Members Intent" enabled in the Discord Developer Portal
   - The bot needs permissions to read messages and view channels

3. Run the test script:
   ```
   python -m src.test_connection
   ```

4. If successful, you should see output showing:
   - Confirmation that the bot connected to Discord
   - The name of your server
   - How many members are in the server
   - A sample list of the first few members

## Attendance Checking Feature

The bot can check which registered attendees are missing from your Discord server:

### Setting Up the Attendance List

1. Prepare a CSV file with your attendees list
   - See `sample_attendees.csv` for the expected format
   - The bot expects names in column 2 (index 1) and team/group info in column 12 (index 11)

2. Set the path to your attendee list in the `.env` file:
   ```
   ATTENDEE_LIST_PATH=./path/to/your/attendees.csv
   ```

### Bot Commands

- `!check_attendance [file_path] [threshold]` - Check which attendees are missing from Discord
  - Generates a report of missing attendees organized by their groups
  - Optionally provide a direct file path (overrides .env setting)
  - Optionally specify a matching threshold (0-100, default: 80)

- `!export_missing [file_path] [threshold]` - Export missing attendees to an Excel file
  - Creates an Excel file with missing attendees and their groups
  - Same parameters as the `check_attendance` command

- `!help_attendance` - Show help information for attendance checking commands

### Name Matching

The bot uses fuzzy string matching to account for slight differences between Discord usernames and real names:

- Discord username `john_doe` will match attendee name `John Doe`
- Discord username `jane.smith` will match attendee name `Jane Smith`
- Discord username `bobby.j` will match attendee name `Bob Johnson` (if threshold is appropriate)

Adjust the similarity threshold to control matching strictness:
- Higher threshold (e.g., 90): More strict, may miss some valid matches
- Lower threshold (e.g., 70): More lenient, may include some false matches

## Running Tests

Run the test suite to verify functionality:

```
python -m tests.run_tests
```

## Usage

Run the bot:

```
python -m src.bot
```

## Features

- Compare Discord server members against an attendee list
- Fuzzy name matching to account for slight differences in names
- Report on missing attendees
- Export results to spreadsheet