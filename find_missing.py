#!/usr/bin/env python3
import os
import sys
import pandas as pd
import datetime
import asyncio
from dotenv import load_dotenv
from src.attendee_manager import AttendeeManager
from src.name_matcher import NameMatcher

# Load environment variables
load_dotenv()

def print_usage():
    print("Usage: python find_missing.py [csv_path] [similarity_threshold]")
    print("  csv_path: Path to the CSV file with attendees (optional)")
    print("  similarity_threshold: Threshold for name matching (0-100, default: 80)")
    print("\nExample: python find_missing.py ./attendees.csv 75")
    print("\nIf csv_path is not provided, the script will use the path from the .env file.")

async def get_discord_members(guild_id, token):
    """
    Get the list of Discord members using the Discord HTTP API directly,
    avoiding the discord.py client which has cleanup issues.
    """
    import aiohttp
    import json

    # Discord API endpoint for getting guild members
    url = f"https://discord.com/api/v10/guilds/{guild_id}/members?limit=1000"
    
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json"
    }
    
    members = []
    
    try:
        async with aiohttp.ClientSession() as session:
            print(f"Connecting to Discord API...")
            
            # Make the API request
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    member_data = await response.json()
                    
                    # Extract member names
                    for member in member_data:
                        user = member.get("user", {})
                        username = user.get("username", "")
                        if username:
                            members.append(username)
                    
                    print(f"Successfully retrieved {len(members)} members from Discord")
                    return members
                else:
                    error_text = await response.text()
                    print(f"ERROR: Failed to get Discord members. Status: {response.status}")
                    print(f"Response: {error_text}")
                    return []
    except Exception as e:
        print(f"ERROR: Exception while fetching Discord members: {str(e)}")
        return []

async def check_attendance(csv_path=None, similarity_threshold=80):
    """
    Check attendance by comparing Discord members against an attendee list.
    """
    try:
        # Get configuration from environment variables
        token = os.getenv('DISCORD_TOKEN')
        guild_id = os.getenv('GUILD_ID')
        
        if not token:
            print("ERROR: No Discord token found. Please set the DISCORD_TOKEN in your .env file.")
            return
        
        if not guild_id:
            print("ERROR: No Guild ID found. Please set the GUILD_ID in your .env file.")
            return
        
        try:
            guild_id = int(guild_id)
        except ValueError:
            print(f"ERROR: Invalid Guild ID: {guild_id}. Must be an integer.")
            return
        
        # Get Discord members
        member_names = await get_discord_members(guild_id, token)
        
        if not member_names:
            print("ERROR: Failed to get Discord members. Please check your token and guild ID.")
            return
        
        # Load attendees
        manager = AttendeeManager(csv_path)
        if not manager.load_attendees():
            print("ERROR: Failed to load attendee list. Check the file path and format.")
            return
        
        attendees = manager.get_attendees()
        attendee_names = manager.get_attendee_names()
        
        print(f"Comparing {len(member_names)} Discord members against {len(attendee_names)} attendees...")
        
        # Match names
        matcher = NameMatcher(similarity_threshold=similarity_threshold)
        missing_attendees_names = matcher.find_missing_attendees(member_names, attendee_names)
        
        # Structure missing attendees by group
        missing_by_group = {}
        for name in missing_attendees_names:
            # Find the attendee's group
            group = next((a['group'] for a in attendees if a['name'] == name), "Unknown")
            
            if group not in missing_by_group:
                missing_by_group[group] = []
            missing_by_group[group].append(name)
        
        # Generate console report
        if not missing_attendees_names:
            report = "✅ All attendees are present in Discord! Great job!"
            print("\n" + report)
        else:
            print(f"\n🔍 Missing Attendees Report ({len(missing_attendees_names)} missing):")
            
            for group, names in sorted(missing_by_group.items()):
                print(f"\nGroup: {group} ({len(names)} missing)")
                for i, name in enumerate(sorted(names)):
                    print(f"  {i+1}. {name}")
        
        # Save text report
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        txt_filename = f"missing_attendees_{timestamp}.txt"
        
        with open(txt_filename, 'w', encoding='utf-8') as f:
            # Write summary
            f.write(f"Missing Attendees Report - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Discord Guild ID: {guild_id}\n")
            f.write(f"Total Discord Members: {len(member_names)}\n")
            f.write(f"Total Attendees: {len(attendees)}\n")
            f.write(f"Missing Attendees: {len(missing_attendees_names)}\n\n")
            
            if not missing_attendees_names:
                f.write("All attendees are present in Discord! Great job!")
            else:
                for group, names in sorted(missing_by_group.items()):
                    f.write(f"Group: {group} ({len(names)} missing)\n")
                    for i, name in enumerate(sorted(names)):
                        f.write(f"  {i+1}. {name}\n")
                    f.write("\n")
        
        print(f"\nText report saved to: {txt_filename}")
        
        # Create Excel file
        if missing_attendees_names:
            missing_data = []
            for name in missing_attendees_names:
                attendee = next((a for a in attendees if a['name'] == name), None)
                if attendee:
                    missing_data.append({
                        'Name': name,
                        'Group': attendee['group']
                    })
            
            df = pd.DataFrame(missing_data)
            excel_filename = f"missing_attendees_{timestamp}.xlsx"
            df.to_excel(excel_filename, index=False)
            
            print(f"Excel report saved to: {excel_filename}")
        
    except Exception as e:
        print(f"ERROR: An error occurred: {str(e)}")

def main():
    # Parse command line arguments
    csv_path = None
    similarity_threshold = 80
    
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help']:
            print_usage()
            sys.exit(0)
        csv_path = sys.argv[1]
    
    if len(sys.argv) > 2:
        try:
            similarity_threshold = int(sys.argv[2])
            if not (0 <= similarity_threshold <= 100):
                print("ERROR: Similarity threshold must be between 0 and 100")
                sys.exit(1)
        except ValueError:
            print(f"ERROR: Invalid similarity threshold: {sys.argv[2]}. Must be an integer.")
            sys.exit(1)
    
    # Run the attendance check
    asyncio.run(check_attendance(csv_path, similarity_threshold))

if __name__ == "__main__":
    main()