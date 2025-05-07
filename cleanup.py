#!/usr/bin/env python3
"""
Cleanup script to remove all generated files from the discord-missing-person-finder.
"""

import os
import glob
import argparse

def cleanup(dry_run=False):
    """
    Remove all generated files.
    
    Args:
        dry_run (bool): If True, only print the files that would be removed without actually removing them.
    """
    # Define patterns for files to remove
    patterns = [
        "output/discord_members_*.csv",
        "output/discord_members_*.txt",
        "output/discord_members.txt",
        "output/edge_cases_*.txt",
        "output/missing_attendees_*.txt",
        "output/missing_attendees_*.xlsx",
        "output/missing_attendees_group_*.txt",
        "output/missing_attendees_group_*.xlsx",
        "output/name_patterns_*.txt",
        "output/matching_debug_*.txt",
        "output/closest_matches.txt",
        "output/processed_attendees.txt",
        "output/processed_discord.txt",
    ]
    
    # Find all files matching patterns
    files_to_remove = []
    for pattern in patterns:
        files_to_remove.extend(glob.glob(pattern))
    
    if not files_to_remove:
        print("No generated files found to remove.")
        return
    
    # Print summary
    print(f"Found {len(files_to_remove)} generated files to remove:")
    for file in sorted(files_to_remove):
        print(f"  - {file}")
    
    # Remove files if not in dry run mode
    if not dry_run:
        removed_count = 0
        for file in files_to_remove:
            try:
                os.remove(file)
                removed_count += 1
            except Exception as e:
                print(f"Error removing {file}: {str(e)}")
        
        print(f"\nSuccessfully removed {removed_count} files.")
    else:
        print("\nDry run mode: No files were actually removed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean up generated files from the discord-missing-person-finder.")
    parser.add_argument("--dry-run", action="store_true", help="Only print files that would be removed without actually removing them.")
    args = parser.parse_args()
    
    cleanup(dry_run=args.dry_run)