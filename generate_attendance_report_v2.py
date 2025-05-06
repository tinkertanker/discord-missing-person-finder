#!/usr/bin/env python3
import os
import csv
import re
import pandas as pd
from datetime import datetime
from difflib import SequenceMatcher

# Script to generate a report of all attendees with their Discord status
# Version 2: Improved matching algorithm using group codes and fuzzy name matching

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
    all_members = []
    
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
                    
                    # Create member dictionary
                    member = {
                        'id': user_id,
                        'display_name': display_name,
                        'username': username,
                        'group_code': group_code,
                        'normalized_name': normalize_name(display_name)
                    }
                    
                    # Store by group code
                    if group_code:
                        if group_code not in discord_members:
                            discord_members[group_code] = []
                        discord_members[group_code].append(member)
                    
                    # Store in all members list
                    all_members.append(member)
        
        print(f"Loaded {len(all_members)} Discord members with {len(discord_members)} group codes")
    except Exception as e:
        print(f"Error loading Discord members: {str(e)}")
    
    return discord_members, all_members

def load_attendees(csv_path):
    """Load attendees from CSV file."""
    attendees = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # Skip header
            
            # Find relevant column indices
            id_col_idx = 0       # CRM Contact Id (index 0)
            name_col_idx = 1     # Full Name (index 1)
            phone_col_idx = 3    # Contact Number (index 3)
            group_col_idx = 11   # group id (index 11)
            
            for row in reader:
                if len(row) > max(name_col_idx, group_col_idx, phone_col_idx):
                    attendee_id = row[id_col_idx].strip()
                    name = row[name_col_idx].strip()
                    phone = row[phone_col_idx].strip()
                    group_code = row[group_col_idx].strip()
                    group_name = row[12].strip() if len(row) > 12 else ""
                    
                    if name:
                        attendees.append({
                            'id': attendee_id,
                            'name': name,
                            'phone': phone,
                            'group_code': group_code,
                            'group_name': group_name,
                            'normalized_name': normalize_name(name)
                        })
        
        print(f"Loaded {len(attendees)} attendees")
    except Exception as e:
        print(f"Error loading attendees: {str(e)}")
    
    return attendees

def normalize_name(name):
    """Normalize a name for better comparison."""
    if not name:
        return ""
    
    # Extract name after slash if present (for "Group Name / Person Name" format)
    if '/' in name:
        parts = name.split('/')
        if len(parts) > 1 and len(parts[1].strip()) > 0:
            name = parts[1].strip()
    
    # Convert to lowercase
    normalized = name.lower()
    
    # Remove special characters
    for char in ['.', ',', '-', '_', '(', ')', '[', ']', '{', '}', ':', ';', '\\']:
        normalized = normalized.replace(char, ' ')
    
    # Trim and remove consecutive spaces
    normalized = ' '.join(normalized.split())
    
    return normalized

def name_similarity(name1, name2):
    """Calculate similarity between two names using sequence matcher."""
    # First check if either name contains the other
    if name1 in name2 or name2 in name1:
        return 0.9  # High similarity score for contained names
    
    # Split names into words
    words1 = name1.split()
    words2 = name2.split()
    
    # Check if any full names match
    for word1 in words1:
        if len(word1) > 2 and word1 in words2:  # Only consider words > 2 chars
            return 0.8  # Good similarity for matching words
    
    # Use sequence matcher for more detailed comparison
    return SequenceMatcher(None, name1, name2).ratio()

def find_discord_match(attendee, discord_members_by_group, all_discord_members):
    """Find a matching Discord member for an attendee using multiple strategies."""
    best_match = None
    best_score = 0
    
    # Strategy 1: Try exact group code match
    if attendee['group_code'] in discord_members_by_group:
        group_members = discord_members_by_group[attendee['group_code']]
        
        # Look for name matches within the group
        for member in group_members:
            similarity = name_similarity(attendee['normalized_name'], member['normalized_name'])
            
            # If very high similarity in the same group, return immediately
            if similarity > 0.8:
                return member, similarity
            
            # Keep track of best match
            if similarity > best_score:
                best_score = similarity
                best_match = member
    
    # If good match found by group, return it
    if best_score > 0.6:
        return best_match, best_score
    
    # Strategy 2: Look across all members for high-similarity matches
    for member in all_discord_members:
        similarity = name_similarity(attendee['normalized_name'], member['normalized_name'])
        
        if similarity > best_score:
            best_score = similarity
            best_match = member
    
    # Return best match if it's good enough
    if best_score > 0.7:
        return best_match, best_score
    
    return None, 0

def generate_attendance_report(attendees_csv, discord_members_file, output_file):
    """Generate a report of all attendees with their Discord status."""
    # Load data
    discord_members_by_group, all_discord_members = load_discord_members(discord_members_file)
    attendees = load_attendees(attendees_csv)
    
    # Create results
    results = []
    
    for attendee in attendees:
        discord_match, similarity = find_discord_match(attendee, discord_members_by_group, all_discord_members)
        
        results.append({
            'ID': attendee['id'],
            'Name': attendee['name'],
            'Phone': attendee['phone'],
            'Group': attendee['group_name'] or attendee['group_code'],
            'Group Code': attendee['group_code'],
            'Status': "Present" if discord_match else "Missing",
            'Discord User': discord_match['display_name'] if discord_match else "X",
            'Match Score': f"{similarity:.2f}" if discord_match else "",
            'Discord Group': discord_match['group_code'] if discord_match else ""
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