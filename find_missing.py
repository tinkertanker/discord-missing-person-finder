#!/usr/bin/env python3
import os
import sys
import discord
import pandas as pd
import asyncio
from dotenv import load_dotenv
from datetime import datetime
from src.attendee_manager import AttendeeManager
from src.name_matcher import NameMatcher

# Load environment variables
load_dotenv()

async def find_missing_attendees(csv_path=None, similarity_threshold=80):
    """
    Find attendees who are missing from the Discord server.
    
    Args:
        csv_path (str, optional): Path to the CSV file with attendees
        similarity_threshold (int, optional): Threshold for name matching (0-100)
        
    Returns:
        None: Results are printed and exported to files
    """
    print("Starting missing attendee finder...")
    
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
    
    # Initialize Discord client with necessary intents
    intents = discord.Intents.default()
    intents.members = True
    client = discord.Client(intents=intents)
    
    # Set up event handler for when the client is ready
    @client.event
    async def on_ready():
        try:
            print(f"Connected to Discord as {client.user}")
            
            # Get the guild (server)
            guild = client.get_guild(guild_id)
            
            if not guild:
                print(f"ERROR: Could not find server with ID {guild_id}")
                await client.close()
                return
            
            print(f"Successfully connected to server: {guild.name} (ID: {guild.id})")
            print(f"Server has {len(guild.members)} members")
            
            # Load attendees
            try:
                manager = AttendeeManager(csv_path)
                if not manager.load_attendees():
                    print("ERROR: Failed to load attendee list. Check the file path and format.")
                    await client.close()
                    return
                
                attendees = manager.get_attendees()
                attendee_names = manager.get_attendee_names()
                groups = manager.get_groups()
                
                print(f"Successfully loaded {len(attendees)} attendees from CSV")
                
                # Get Discord members
                members = guild.members
                member_names = [member.name for member in members]
                
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
                    print("\n✅ All attendees are present in Discord! Great job!")
                else:
                    print(f"\n🔍 Missing Attendees Report ({len(missing_attendees_names)} missing):")
                    
                    for group, names in sorted(missing_by_group.items()):
                        print(f"\nGroup: {group} ({len(names)} missing)")
                        for i, name in enumerate(sorted(names)):
                            print(f"  {i+1}. {name}")
                
                # Save text report
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                txt_filename = f"missing_attendees_{timestamp}.txt"
                
                with open(txt_filename, 'w', encoding='utf-8') as f:
                    # Write summary
                    f.write(f"Missing Attendees Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Server: {guild.name} (ID: {guild.id})\n")
                    f.write(f"Total Discord Members: {len(members)}\n")
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
                print(f"ERROR: An error occurred while processing attendees: {str(e)}")
            
            # Close the client
            await client.close()
            
        except Exception as e:
            print(f"ERROR: {str(e)}")
            await client.close()
    
    # Connect to Discord
    try:
        await client.start(token)
    except discord.errors.LoginFailure:
        print("ERROR: Invalid Discord token. Please check your DISCORD_TOKEN in the .env file.")
    except Exception as e:
        print(f"ERROR: Failed to connect to Discord: {str(e)}")
    finally:
        # Ensure everything is properly closed
        if not client.is_closed():
            await client.close()
        
        # Give the event loop time to close connections
        pending = asyncio.all_tasks(asyncio.get_event_loop())
        for task in pending:
            if not task.done():
                task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

def print_usage():
    print("Usage: python find_missing.py [csv_path] [similarity_threshold]")
    print("  csv_path: Path to the CSV file with attendees (optional)")
    print("  similarity_threshold: Threshold for name matching (0-100, default: 80)")
    print("\nExample: python find_missing.py ./attendees.csv 75")
    print("\nIf csv_path is not provided, the script will use the path from the .env file.")

if __name__ == "__main__":
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
    
    # Run the async function
    asyncio.run(find_missing_attendees(csv_path, similarity_threshold))