#!/usr/bin/env python3
import os
import sys
import pandas as pd
import datetime
import asyncio
import re
import json
from dotenv import load_dotenv
from src.attendee_manager import AttendeeManager
from src.name_matcher import NameMatcher
from src.group_matcher import GroupMatcher

# Load environment variables
load_dotenv()

def print_usage():
    print("Usage: python find_missing.py [csv_path] [similarity_threshold] [options]")
    print("  csv_path: Path to the CSV file with attendees (optional)")
    print("  similarity_threshold: Threshold for name matching (0-100, default: 80)")
    print("\nOptions:")
    print("  --name-only: Use only name matching (without group-based matching)")
    print("  --analyze-groups: Run group analysis tool without full matching")
    print("  --test-groups: Same as --analyze-groups")
    print("  -h, --help: Show this help message")
    print("\nExamples:")
    print("  python find_missing.py ./attendees.csv 75")
    print("  python find_missing.py ./attendees.csv 80 --name-only")
    print("  python find_missing.py ./attendees.csv --analyze-groups")
    print("\nIf csv_path is not provided, the script will use the path from the .env file.")
    print("The default behavior is to use group-based matching with cat-x-grp-y roles in Discord")

async def get_discord_members(guild_id, token):
    """
    Get the list of Discord members using the Discord HTTP API directly,
    avoiding the discord.py client which has cleanup issues.
    Retrieves member details including roles and extracts cat-x-grp-y patterns.
    """
    import aiohttp
    import json

    # Discord API endpoints
    members_url = f"https://discord.com/api/v10/guilds/{guild_id}/members?limit=1000"
    roles_url = f"https://discord.com/api/v10/guilds/{guild_id}/roles"
    
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json"
    }
    
    discord_members = []
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    try:
        async with aiohttp.ClientSession() as session:
            print(f"Connecting to Discord API...")
            
            # Get roles first
            async with session.get(roles_url, headers=headers) as roles_response:
                if roles_response.status != 200:
                    error_text = await roles_response.text()
                    print(f"ERROR: Failed to get Discord roles. Status: {roles_response.status}")
                    print(f"Response: {error_text}")
                    return []
                
                roles_data = await roles_response.json()
                # Create a map of role ID to role name
                role_map = {role['id']: role['name'] for role in roles_data}
            
            # Get members
            async with session.get(members_url, headers=headers) as response:
                if response.status == 200:
                    member_data = await response.json()
                    
                    # Used for debugging and file export
                    member_text_rows = []
                    member_csv_rows = []
                    
                    # Extract member details including roles
                    for member in member_data:
                        user = member.get("user", {})
                        user_id = user.get("id", "")
                        username = user.get("username", "")
                        display_name = member.get("nick") or username
                        
                        # Extract roles
                        role_ids = member.get("roles", [])
                        role_names = [role_map.get(role_id, "") for role_id in role_ids if role_id in role_map]
                        
                        # Extract cat-x-grp-y pattern from roles
                        group_code = ""
                        for role_name in role_names:
                            match = re.search(r'(cat-\d+-grp-\d+)', role_name)
                            if match:
                                group_code = match.group(1)
                                break
                        
                        # Add member to the list with all details
                        if username:
                            discord_members.append({
                                'id': user_id,
                                'username': username,
                                'display_name': display_name,
                                'roles': role_names,
                                'group_code': group_code
                            })
                            
                            # Add to text format for file export
                            member_text_rows.append(f"{user_id}|{display_name}|{username}|{display_name}|{group_code}|{','.join(role_names)}")
                            member_csv_rows.append([user_id, display_name, username, display_name, group_code, ",".join(role_names)])
                    
                    # Ensure output directory exists
                    os.makedirs("output", exist_ok=True)
                    
                    # Save member data to files for debugging and further analysis
                    with open(f"output/discord_members_{timestamp}.txt", 'w', encoding='utf-8') as f:
                        f.write("\n".join(member_text_rows))
                    
                    # Save as CSV too
                    with open(f"output/discord_members_{timestamp}.csv", 'w', encoding='utf-8', newline='') as f:
                        writer = pd.DataFrame(member_csv_rows, columns=["ID", "DisplayName", "Username", "Nickname", "GroupCode", "Roles"])
                        writer.to_csv(f, index=False)
                    
                    print(f"Successfully retrieved {len(discord_members)} members from Discord")
                    print(f"Member data saved to: discord_members_{timestamp}.txt and discord_members_{timestamp}.csv")
                    return discord_members
                else:
                    error_text = await response.text()
                    print(f"ERROR: Failed to get Discord members. Status: {response.status}")
                    print(f"Response: {error_text}")
                    return []
    except Exception as e:
        print(f"ERROR: Exception while fetching Discord members: {str(e)}")
        return []

async def check_attendance(csv_path=None, similarity_threshold=80, use_group_matcher=True):
    """
    Check attendance by comparing Discord members against an attendee list.
    Uses group-based matching (cat-x-grp-y role to column 12) for more accurate results.
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
        
        # Get Discord members with role information
        discord_members = await get_discord_members(guild_id, token)
        
        if not discord_members:
            print("ERROR: Failed to get Discord members. Please check your token and guild ID.")
            return
        
        # Load attendees
        manager = AttendeeManager(csv_path)
        if not manager.load_attendees():
            print("ERROR: Failed to load attendee list. Check the file path and format.")
            return
        
        attendees = manager.get_attendees()
        attendee_names = manager.get_attendee_names()
        
        # Create timestamp for output files
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Ensure output directory exists
        os.makedirs("output", exist_ok=True)
        
        # Create discord_members.txt file for GroupMatcher
        with open("output/discord_members.txt", "w", encoding="utf-8") as f:
            for member in discord_members:
                f.write(f"{member['id']}|{member['display_name']}|{member['username']}|{member['display_name']}|{member['group_code']}|{','.join(member['roles'])}\n")
        
        if use_group_matcher:
            print(f"Using group-based matching to compare {len(discord_members)} Discord members against {len(attendee_names)} attendees...")
            
            # Use GroupMatcher for group-first matching
            matcher = GroupMatcher(similarity_threshold=similarity_threshold, debug=True)
            
            # Find missing attendees using the GroupMatcher
            results = matcher.find_missing_attendees("output/discord_members.txt", csv_path)
            missing_attendees = results['missing']
            missing_by_group = results['missing_by_group']
            missing_attendees_names = [attendee['name'] for attendee in missing_attendees]
            
            # Generate reports
            txt_filename, excel_filename = matcher.generate_reports(results)
            
            # Generate additional debug reports
            with open(f"output/name_patterns_{timestamp}.txt", "w", encoding="utf-8") as f:
                f.write("Group Codes in Discord Roles:\n")
                group_codes = set()
                for member in discord_members:
                    if member['group_code']:
                        group_codes.add(member['group_code'])
                
                for code in sorted(group_codes):
                    f.write(f"- {code}\n")
                
                f.write("\nAttendee Groups in CSV (Column 12):\n")
                attendee_groups = set()
                for attendee in attendees:
                    if attendee['group']:
                        attendee_groups.add(attendee['group'])
                
                for group in sorted(attendee_groups):
                    f.write(f"- {group}\n")
                
                f.write("\nGroup Mapping:\n")
                for discord_group, attendee_group in results.get('group_mapping', {}).items():
                    f.write(f"Discord: {discord_group} → Attendee: {attendee_group}\n")
        else:
            # Fall back to name-only matching if requested
            print(f"Using name-only matching to compare {len(discord_members)} Discord members against {len(attendee_names)} attendees...")
            
            # Extract just the display names for name-based matching
            member_names = [member['display_name'] for member in discord_members]
            
            # Match names using the old method
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
            
            # Save text report
            txt_filename = f"output/missing_attendees_{timestamp}.txt"
            
            # Calculate group totals for the text report
            group_totals = {}
            for attendee in attendees:
                group = attendee['group']
                if group not in group_totals:
                    group_totals[group] = 0
                group_totals[group] += 1
            
            with open(txt_filename, 'w', encoding='utf-8') as f:
                # Write summary
                f.write(f"Missing Attendees Report - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Discord Guild ID: {guild_id}\n")
                f.write(f"Total Discord Members: {len(member_names)}\n")
                f.write(f"Total Attendees: {len(attendees)}\n")
                f.write(f"Missing Attendees: {len(missing_attendees_names)} out of {len(attendees)}\n\n")
                
                if not missing_attendees_names:
                    f.write("All attendees are present in Discord! Great job!")
                else:
                    for group, names in sorted(missing_by_group.items()):
                        total_in_group = group_totals.get(group, 0)
                        f.write(f"Group: {group} ({len(names)}/{total_in_group} missing)\n")
                        for i, name in enumerate(sorted(names)):
                            f.write(f"  {i+1}. {name}\n")
                        f.write("\n")
            
            # Create Excel file
            if missing_attendees_names:
                missing_data = []
                for name in missing_attendees_names:
                    attendee = next((a for a in attendees if a['name'] == name), None)
                    if attendee:
                        missing_data.append({
                            'ID': attendee.get('id', ''),
                            'Name': name,
                            'Email': attendee.get('email', ''),
                            'Phone': attendee.get('phone', ''),
                            'Group': attendee['group']
                        })
                
                df = pd.DataFrame(missing_data)
                excel_filename = f"output/missing_attendees_{timestamp}.xlsx"
                df.to_excel(excel_filename, index=False)
        
        # Generate console report
        if not missing_attendees_names:
            report = "✅ All attendees are present in Discord! Great job!"
            print("\n" + report)
        else:
            print(f"\n🔍 Missing Attendees Report ({len(missing_attendees_names)} out of {len(attendees)} missing):")
            
            if use_group_matcher and 'attendee_groups' in results:
                # For GroupMatcher, calculate group totals
                for group, names in sorted(missing_by_group.items()):
                    # Find total in group
                    total_in_group = 0
                    for group_name, attendees_list in results['attendee_groups'].items():
                        if group == group_name:
                            total_in_group = len(attendees_list)
                            break
                    
                    print(f"\nGroup: {group} ({len(names)}/{total_in_group} missing)")
                    # Check if names contains dictionaries or strings
                    if names and isinstance(names[0], dict):
                        for i, attendee in enumerate(names):
                            print(f"  {i+1}. {attendee['name']}")
                    else:
                        for i, name in enumerate(names):
                            print(f"  {i+1}. {name}")
            else:
                # For NameMatcher, calculate group totals manually
                group_totals = {}
                for attendee in attendees:
                    group = attendee['group']
                    if group not in group_totals:
                        group_totals[group] = 0
                    group_totals[group] += 1
                
                for group, names in sorted(missing_by_group.items()):
                    total_in_group = group_totals.get(group, 0)
                    print(f"\nGroup: {group} ({len(names)}/{total_in_group} missing)")
                    for i, name in enumerate(sorted(names)):
                        print(f"  {i+1}. {name}")
        
        print(f"\nText report saved to: {txt_filename}")
        if 'excel_filename' in locals():
            print(f"Excel report saved to: {excel_filename}")
        
        # Create a file with edge cases and debug information
        with open(f"output/edge_cases_{timestamp}.txt", "w", encoding="utf-8") as f:
            f.write(f"Edge Cases Report - {datetime.datetime.now()}\n")
            f.write(f"Similarity Threshold: {similarity_threshold}\n")
            f.write(f"Matcher: {'GroupMatcher' if use_group_matcher else 'NameMatcher'}\n\n")
            
            f.write("This report shows the structure of group codes and how they map between Discord roles (cat-x-grp-y) and attendee CSV column 12.\n\n")
            
            f.write("Discord Group Codes (from roles):\n")
            group_counts = {}
            for member in discord_members:
                group_code = member['group_code']
                if group_code:
                    group_counts[group_code] = group_counts.get(group_code, 0) + 1
            
            for group, count in sorted(group_counts.items()):
                f.write(f"  {group}: {count} members\n")
            
            f.write("\nAttendee Group Codes (from CSV column 12):\n")
            attendee_group_counts = {}
            for attendee in attendees:
                group = attendee['group']
                if group:
                    attendee_group_counts[group] = attendee_group_counts.get(group, 0) + 1
            
            for group, count in sorted(attendee_group_counts.items()):
                f.write(f"  {group}: {count} attendees\n")
            
            if use_group_matcher and 'group_mapping' in results:
                f.write("\nGroup Mapping:\n")
                for discord_group, attendee_group in results['group_mapping'].items():
                    f.write(f"  {discord_group} → {attendee_group}\n")
        
        print(f"Debug information saved to: edge_cases_{timestamp}.txt")
    except Exception as e:
        print(f"ERROR: An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()

async def analyze_groups(csv_path=None):
    """
    Analyze the group codes in Discord roles and how they map to attendee groups in CSV column 12.
    This is a test command to verify the group matching functionality.
    """
    try:
        # Get configuration from environment variables
        token = os.getenv('DISCORD_TOKEN')
        guild_id = os.getenv('GUILD_ID')
        
        if not token or not guild_id:
            print("ERROR: Missing Discord configuration. Please set DISCORD_TOKEN and GUILD_ID in .env file.")
            return
        
        try:
            guild_id = int(guild_id)
        except ValueError:
            print(f"ERROR: Invalid Guild ID: {guild_id}. Must be an integer.")
            return
        
        # Get Discord members with role information
        discord_members = await get_discord_members(guild_id, token)
        
        if not discord_members:
            print("ERROR: Failed to get Discord members. Please check your token and guild ID.")
            return
        
        # Load attendees
        manager = AttendeeManager(csv_path)
        if not manager.load_attendees():
            print("ERROR: Failed to load attendee list. Check the file path and format.")
            return
        
        attendees = manager.get_attendees()
        
        # Ensure output directory exists
        os.makedirs("output", exist_ok=True)
        
        # Create the discord_members.txt file for GroupMatcher
        with open("output/discord_members.txt", "w", encoding="utf-8") as f:
            for member in discord_members:
                f.write(f"{member['id']}|{member['display_name']}|{member['username']}|{member['display_name']}|{member['group_code']}|{','.join(member['roles'])}\n")
        
        # Create a test instance of GroupMatcher with debug mode
        matcher = GroupMatcher(similarity_threshold=70, debug=True)
        
        # Analyze groups without doing matching
        print("\n=== Group Analysis Report ===\n")
        
        # Discord groups
        print("Discord Group Codes (from cat-x-grp-y roles):")
        group_codes = {}
        for member in discord_members:
            code = member['group_code']
            if code:
                group_codes[code] = group_codes.get(code, 0) + 1
        
        for code, count in sorted(group_codes.items()):
            print(f"  {code}: {count} members")
        
        # Attendee groups
        print("\nAttendee Groups (from CSV column 12):")
        attendee_groups = {}
        for attendee in attendees:
            group = attendee['group']
            if group:
                attendee_groups[group] = attendee_groups.get(group, 0) + 1
        
        for group, count in sorted(attendee_groups.items()):
            print(f"  {group}: {count} attendees")
        
        # Load discord members and attendees in GroupMatcher
        discord_members_data, discord_groups = matcher.load_discord_members("output/discord_members.txt")
        attendee_data, attendee_groups = matcher.load_attendees(csv_path)
        
        # Map groups using GroupMatcher's algorithm
        print("\nGroup Mapping Analysis:")
        group_mapping = matcher.map_groups(discord_groups, attendee_groups)
        
        for discord_group, attendee_group in sorted(group_mapping.items()):
            print(f"  Discord: {discord_group} → Attendee: {attendee_group}")
        
        # Output to a file
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        with open(f"output/matching_debug_{timestamp}.txt", "w", encoding="utf-8") as f:
            f.write("Group Matching Analysis Report\n")
            f.write("=============================\n\n")
            
            f.write("Discord Group Codes:\n")
            for code, count in sorted(group_codes.items()):
                f.write(f"  {code}: {count} members\n")
            
            f.write("\nAttendee Groups:\n")
            for group, count in sorted(attendee_groups.items()):
                f.write(f"  {group}: {count} attendees\n")
            
            f.write("\nGroup Mapping:\n")
            for discord_group, attendee_group in sorted(group_mapping.items()):
                f.write(f"  {discord_group} → {attendee_group}\n")
        
        print(f"\nAnalysis report saved to: matching_debug_{timestamp}.txt")
        
    except Exception as e:
        print(f"ERROR: An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    # Parse command line arguments
    csv_path = None
    similarity_threshold = 80
    use_group_matcher = True  # Default to using group-based matching
    
    # Check for help flag first
    if any(arg in ['-h', '--help'] for arg in sys.argv):
        print_usage()
        sys.exit(0)
    
    # Check for test/analyze mode
    if any(arg in ['--analyze-groups', '--test-groups'] for arg in sys.argv):
        # Remove the flag
        for flag in ['--analyze-groups', '--test-groups']:
            if flag in sys.argv:
                sys.argv.remove(flag)
        
        # Get CSV path if provided
        if len(sys.argv) > 1:
            csv_path = sys.argv[1]
        
        print("Running group analysis tool...")
        asyncio.run(analyze_groups(csv_path))
        sys.exit(0)
    
    # Check for name-only flag (can be in any position)
    if '--name-only' in sys.argv:
        use_group_matcher = False
        # Remove the flag from argv for easier positional arg processing
        sys.argv.remove('--name-only')
    
    # Process positional arguments
    if len(sys.argv) > 1:
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
    
    # Print the mode being used
    print(f"Using {'group-based' if use_group_matcher else 'name-only'} matching with threshold: {similarity_threshold}")
    
    # Run the attendance check
    asyncio.run(check_attendance(csv_path, similarity_threshold, use_group_matcher))

if __name__ == "__main__":
    main()