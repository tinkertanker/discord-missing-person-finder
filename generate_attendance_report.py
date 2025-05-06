#!/usr/bin/env python3
import os
import csv
import re
import pandas as pd
from datetime import datetime

# Script to generate a report of all attendees with their Discord status

def extract_group_code(role_text):
    """Extract cat-x-grp-y pattern from Discord role info."""
    if not role_text:
        return ""
    
    match = re.search(r'(cat-\d+-grp-\d+)', role_text)
    if match:
        return match.group(1)
    return ""

def load_discord_members(discord_file):
    """Load Discord members from the text file."""
    discord_members = {}
    
    try:
        with open(discord_file, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) >= 5:  # ID|DisplayName|Username|Nickname|GroupCode|Roles
                    user_id = parts[0]
                    display_name = parts[1]
                    username = parts[2]
                    group_code = parts[4] if len(parts) > 4 and parts[4] else ""
                    
                    # If group_code is empty, try to extract from roles
                    if not group_code and len(parts) > 5:
                        group_code = extract_group_code(parts[5])
                    
                    # Store in dictionary
                    discord_members[group_code] = discord_members.get(group_code, [])
                    discord_members[group_code].append({
                        'id': user_id,
                        'display_name': display_name,
                        'username': username,
                        'group_code': group_code
                    })
    except Exception as e:
        print(f"Error loading Discord members: {str(e)}")
    
    return discord_members

def load_attendees(csv_path):
    """Load attendees from CSV file."""
    attendees = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # Skip header
            
            # Find relevant column indices
            name_col_idx = 1  # Full Name (index 1)
            group_col_idx = 11  # group id (index 11)
            
            for row in reader:
                if len(row) > max(name_col_idx, group_col_idx):
                    name = row[name_col_idx].strip()
                    group_code = row[group_col_idx].strip()
                    group_name = row[12].strip() if len(row) > 12 else ""
                    
                    if name:
                        attendees.append({
                            'name': name,
                            'group_code': group_code,
                            'group_name': group_name
                        })
    except Exception as e:
        print(f"Error loading attendees: {str(e)}")
    
    return attendees

def normalize_name(name):
    """Normalize a name for better comparison."""
    if not name:
        return ""
    
    # Convert to lowercase
    normalized = name.lower()
    
    # Remove special characters
    for char in ['.', ',', '-', '_', '(', ')', '[', ']', '{', '}', ':', ';', '/', '\\']:
        normalized = normalized.replace(char, ' ')
    
    # Trim and remove consecutive spaces
    normalized = ' '.join(normalized.split())
    
    return normalized

def find_discord_match(attendee, discord_members_by_group):
    """Find a matching Discord member for an attendee."""
    # Try to match by group first
    group_code = attendee['group_code']
    
    # Fall back to searching across all Discord members if no group match
    all_group_codes = list(discord_members_by_group.keys())
    
    # Try exact group match first
    if group_code in discord_members_by_group:
        group_members = discord_members_by_group[group_code]
        
        # Normalize attendee name
        attendee_name_norm = normalize_name(attendee['name'])
        
        # Check for name matches within the group
        for member in group_members:
            display_name_norm = normalize_name(member['display_name'])
            
            # Check for exact or fuzzy match
            if (attendee_name_norm in display_name_norm or
                display_name_norm in attendee_name_norm or
                any(word in display_name_norm for word in attendee_name_norm.split() if len(word) > 3)):
                return member
    
    # If not found, search all members (future enhancement)
    # This would be slower but more comprehensive
    
    return None

def generate_attendance_report(attendees_csv, discord_members_file, output_file):
    """Generate a report of all attendees with their Discord status."""
    # Load data
    discord_members_by_group = load_discord_members(discord_members_file)
    attendees = load_attendees(attendees_csv)
    
    # Create results
    results = []
    
    for attendee in attendees:
        discord_match = find_discord_match(attendee, discord_members_by_group)
        
        results.append({
            'Name': attendee['name'],
            'Group': attendee['group_name'] or attendee['group_code'],
            'Group Code': attendee['group_code'],
            'Status': "Present" if discord_match else "Missing",
            'Discord User': discord_match['display_name'] if discord_match else "X"
        })
    
    # Save to Excel
    df = pd.DataFrame(results)
    df.to_excel(output_file, index=False)
    print(f"Attendance report saved to: {output_file}")
    
    # Summary
    present_count = sum(1 for r in results if r['Status'] == "Present")
    missing_count = sum(1 for r in results if r['Status'] == "Missing")
    
    print(f"Total Attendees: {len(results)}")
    print(f"Present in Discord: {present_count}")
    print(f"Missing from Discord: {missing_count}")
    
    # Also generate group summary
    group_summary = {}
    for r in results:
        group = r['Group']
        if group not in group_summary:
            group_summary[group] = {"total": 0, "present": 0, "missing": 0}
        
        group_summary[group]["total"] += 1
        if r['Status'] == "Present":
            group_summary[group]["present"] += 1
        else:
            group_summary[group]["missing"] += 1
    
    print("\nGroup Summary:")
    for group, stats in sorted(group_summary.items()):
        print(f"{group}: {stats['present']}/{stats['total']} present, {stats['missing']} missing")

if __name__ == "__main__":
    import sys
    
    # Default paths
    attendees_csv = "./attendees.csv"
    discord_members_file = "./discord_members.txt"
    
    # Generate timestamp for output file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"attendance_report_{timestamp}.xlsx"
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        attendees_csv = sys.argv[1]
    
    if len(sys.argv) > 2:
        discord_members_file = sys.argv[2]
    
    if len(sys.argv) > 3:
        output_file = sys.argv[3]
    
    generate_attendance_report(attendees_csv, discord_members_file, output_file)