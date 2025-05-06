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