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