#!/usr/bin/env python3
"""
Name Matching Analysis Tool

This script loads Discord members and attendee lists, then performs
detailed matching analysis to help debug and improve the matching algorithm.

Usage:
  python -m src.analyze_matching [--threshold=N] [--sample=N] [--discord-file=PATH] [--attendee-file=PATH]

Options:
  --threshold=N         Set matching similarity threshold (default: 80)
  --sample=N            Number of attendee samples to analyze (default: 10)
  --discord-file=PATH   Path to discord members file (default: discord_members.txt)
  --attendee-file=PATH  Path to attendees file (default: from .env)
"""

import os
import sys
import csv
import argparse
import pandas as pd
from datetime import datetime
from src.name_matcher import NameMatcher
from src.test_connection import export_discord_members
import asyncio

def load_discord_members(filename="discord_members.txt"):
    """
    Load Discord member information from a file.
    
    Args:
        filename (str): Path to the Discord members file
        
    Returns:
        list: List of Discord member names
    """
    try:
        members = []
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) >= 3:  # ID|DisplayName|Username|Nickname
                    # Use nickname if available, otherwise use display name
                    name = parts[3] if len(parts) > 3 and parts[3] else parts[2]
                    members.append(name)
        
        print(f"Loaded {len(members)} Discord members from {filename}")
        return members
    except FileNotFoundError:
        print(f"Error: Discord members file '{filename}' not found.")
        print("Run 'DISCORD_COMMAND=export python -m src.test_connection' to generate the file.")
        sys.exit(1)

def load_attendees(filename=None):
    """
    Load attendee list from CSV.
    
    Args:
        filename (str, optional): Path to the attendee list file
        
    Returns:
        list: List of attendee names
    """
    if not filename:
        # Try to get from environment
        from dotenv import load_dotenv
        load_dotenv()
        filename = os.getenv('ATTENDEE_LIST_PATH')
        
    if not filename or not os.path.exists(filename):
        print(f"Error: Attendee list file '{filename}' not found.")
        print("Please specify with --attendee-file or set ATTENDEE_LIST_PATH in .env")
        sys.exit(1)
    
    try:
        # Try to read as CSV
        attendees = []
        df = pd.read_csv(filename)
        
        # Assume name is in the second column (index 1)
        if len(df.columns) >= 2:
            name_col = df.iloc[:, 1]
            for _, name in name_col.items():
                if pd.notna(name) and isinstance(name, str) and name.strip():
                    attendees.append(name.strip())
        
        print(f"Loaded {len(attendees)} attendees from {filename}")
        return attendees
    except Exception as e:
        print(f"Error loading attendee list: {str(e)}")
        sys.exit(1)

def find_edge_cases(matcher, discord_users, attendee_names, threshold=80, n=10):
    """
    Find edge cases that are close to the threshold.
    
    Args:
        matcher: The NameMatcher instance
        discord_users: List of Discord usernames
        attendee_names: List of attendee names
        threshold: Similarity threshold
        n: Number of edge cases to find
        
    Returns:
        list: Edge cases near the threshold
    """
    edge_cases = []
    
    # Test each attendee against all Discord users
    for attendee in attendee_names:
        best_score = 0
        best_discord = None
        best_details = None
        
        for discord in discord_users:
            _, score, details = matcher.is_match(discord, attendee)
            if abs(score - threshold) < 15:  # Find names close to threshold
                edge_cases.append((abs(score - threshold), attendee, discord, score, details))
            
            # Also track the best match
            if score > best_score:
                best_score = score
                best_discord = discord
                best_details = details
        
        # If no edge cases but the best score is low
        if best_score < threshold * 0.8 and best_discord:  # Names with very low match scores
            edge_cases.append((100, attendee, best_discord, best_score, best_details))
    
    # Sort by closeness to threshold and take top N
    edge_cases.sort()
    return edge_cases[:n]

def analyze_group_format(attendee_names):
    """
    Analyze the format of group information in attendee names.
    
    Args:
        attendee_names: List of attendee names
        
    Returns:
        dict: Statistics about group format patterns
    """
    patterns = {
        "contains_slash": 0,
        "contains_dash": 0,
        "contains_parens": 0,
        "contains_brackets": 0,
        "contains_comma": 0,
        "total": len(attendee_names)
    }
    
    examples = {
        "contains_slash": [],
        "contains_dash": [],
        "contains_parens": [],
        "contains_brackets": [],
        "contains_comma": []
    }
    
    for name in attendee_names:
        if '/' in name:
            patterns["contains_slash"] += 1
            if len(examples["contains_slash"]) < 5:
                examples["contains_slash"].append(name)
        
        if '-' in name:
            patterns["contains_dash"] += 1
            if len(examples["contains_dash"]) < 5:
                examples["contains_dash"].append(name)
        
        if '(' in name or ')' in name:
            patterns["contains_parens"] += 1
            if len(examples["contains_parens"]) < 5:
                examples["contains_parens"].append(name)
        
        if '[' in name or ']' in name:
            patterns["contains_brackets"] += 1
            if len(examples["contains_brackets"]) < 5:
                examples["contains_brackets"].append(name)
                
        if ',' in name:
            patterns["contains_comma"] += 1
            if len(examples["contains_comma"]) < 5:
                examples["contains_comma"].append(name)
    
    return patterns, examples

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Name Matching Analysis Tool")
    parser.add_argument("--threshold", type=int, default=80, 
                        help="Similarity threshold (0-100)")
    parser.add_argument("--sample", type=int, default=10, 
                        help="Number of samples to analyze")
    parser.add_argument("--discord-file", type=str, default="discord_members.txt",
                        help="Path to discord members file")
    parser.add_argument("--attendee-file", type=str, default=None,
                        help="Path to attendees file")
    args = parser.parse_args()
    
    # Check if discord members file exists, if not, generate it
    if not os.path.exists(args.discord_file):
        print(f"Discord members file '{args.discord_file}' not found.")
        print("Generating file by connecting to Discord...")
        asyncio.run(export_discord_members())
    
    # Load data
    discord_members = load_discord_members(args.discord_file)
    attendees = load_attendees(args.attendee_file)
    
    # Create matcher with debug mode
    matcher = NameMatcher(similarity_threshold=args.threshold, debug=True)
    
    # Generate timestamp for report files
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Generate comprehensive matching debug report
    print(f"Generating matching debug report for {args.sample} sample attendees...")
    debug_file = matcher.generate_matching_debug_report(
        discord_members, attendees, sample_size=args.sample
    )
    print(f"Debug report generated: {debug_file}")
    
    # Find and analyze edge cases
    print("\nAnalyzing edge cases (matches near threshold)...")
    edge_cases = find_edge_cases(
        matcher, discord_members, attendees, 
        threshold=args.threshold, n=args.sample
    )
    
    edge_case_file = f"edge_cases_{timestamp}.txt"
    with open(edge_case_file, 'w', encoding='utf-8') as f:
        f.write(f"Edge Cases Analysis - {datetime.now()}\n")
        f.write(f"Similarity Threshold: {args.threshold}\n")
        f.write("-" * 80 + "\n\n")
        
        for i, (distance, attendee, discord, score, details) in enumerate(edge_cases):
            f.write(f"EDGE CASE {i+1}:\n")
            f.write(f"Attendee: {attendee}\n")
            f.write(f"Discord: {discord}\n")
            f.write(f"Score: {score} (Distance from threshold: {distance})\n")
            f.write(f"Normalized Attendee: {details['norm_attendee']}\n")
            f.write(f"Normalized Discord: {details['norm_discord']}\n")
            f.write(f"Best method: {details['best_method']}\n")
            f.write(f"Individual scores: {details['scores']}\n")
            f.write("-" * 60 + "\n\n")
    
    print(f"Edge cases analysis saved to: {edge_case_file}")
    
    # Analyze name patterns
    print("\nAnalyzing attendee name patterns...")
    patterns, examples = analyze_group_format(attendees)
    
    pattern_file = f"name_patterns_{timestamp}.txt"
    with open(pattern_file, 'w', encoding='utf-8') as f:
        f.write(f"Name Pattern Analysis - {datetime.now()}\n")
        f.write(f"Total Attendees: {patterns['total']}\n")
        f.write("-" * 80 + "\n\n")
        
        for pattern, count in patterns.items():
            if pattern == 'total':
                continue
            percentage = (count / patterns['total']) * 100
            f.write(f"{pattern}: {count} ({percentage:.1f}%)\n")
            
            if examples[pattern]:
                f.write("Examples:\n")
                for example in examples[pattern]:
                    f.write(f"  - {example}\n")
            f.write("\n")
    
    print(f"Name pattern analysis saved to: {pattern_file}")
    
    # Generate closest matches file
    print("\nGenerating closest matches report...")
    matcher.find_matches_for_discord_users(discord_members[:100], attendees[:100])
    print("Closest matches saved to: closest_matches.txt")
    print("Processed attendees saved to: processed_attendees.txt")
    print("Processed Discord names saved to: processed_discord.txt")
    
    print("\nAnalysis complete! Review the generated files to improve matching.")

if __name__ == "__main__":
    main()