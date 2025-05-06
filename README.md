# Discord Missing Person Finder

A tool for identifying registered attendees who are missing from your Discord server.

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
4. Copy `.env.example` to `.env` and fill in your Discord token and server settings:
   ```
   DISCORD_TOKEN=your_actual_token_here
   GUILD_ID=your_server_id_here
   ATTENDEE_LIST_PATH=./path/to/your/attendees.csv
   ```

## Using the Missing Person Finder

The tool provides a simple way to identify registered attendees who are not in your Discord server:

1. Prepare your attendee list as a CSV file:
   - Names should be in column 2 (index 1)
   - Group/team info should be in column 12 (index 11)
   - See `sample_attendees.csv` for an example format

2. Run the script:
   ```
   python find_missing.py [csv_path] [similarity_threshold]
   ```
   
   - `csv_path` (optional): Path to your attendee CSV file (overrides .env setting)
   - `similarity_threshold` (optional): Matching threshold between 0-100 (default: 80)

3. The script will:
   - Connect to Discord using your bot token
   - Read the attendee list from the CSV file
   - Compare Discord member names with the attendee list
   - Identify missing attendees
   - Generate reports in both text and Excel formats

## Name Matching

The tool uses fuzzy string matching to handle differences between Discord usernames and real names:

- Discord username `john_doe` will match attendee name `John Doe`
- Discord username `jane.smith` will match attendee name `Jane Smith`
- Discord username `bobby.j` can match attendee name `Bob Johnson` (depending on threshold)

Adjusting the similarity threshold controls matching strictness:
- Higher threshold (e.g., 90): More strict, may miss some valid matches
- Lower threshold (e.g., 70): More lenient, may include some false matches

## Testing Your Discord Connection

To verify your Discord bot token and environment are set up correctly:

```
python -m src.test_connection
```

If successful, you should see output showing your bot connected to Discord, the name of your server, member count, and a sample of members.

## Features

- Fast identification of missing attendees
- Fuzzy name matching to handle Discord username variations
- Group/team-based reporting
- Export to both text and Excel formats
- Adjustable matching threshold